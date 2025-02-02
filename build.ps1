#!/usr/bin/env pwsh

$number_of_build_workers = 8
$enable_cuda = $true
$use_vcpkg = $true
$use_ninja = $true
$force_cpp_build = $false

#$additional_build_setup = " -DCMAKE_CUDA_ARCHITECTURES=30"


$CMAKE_EXE = Get-Command cmake | Select-Object -ExpandProperty Definition
$NINJA_EXE = Get-Command ninja | Select-Object -ExpandProperty Definition

if (-Not $CMAKE_EXE) {
  throw "Could not find CMake, please install it"
}
else {
  Write-Host "Using CMake from ${CMAKE_EXE}"
}

if (-Not $NINJA_EXE -and $use_ninja) {
  throw "Could not find Ninja, please install it"
}
else {
  Write-Host "Using Ninja from ${NINJA_EXE}"
}

function getProgramFiles32bit() {
  $out = ${env:PROGRAMFILES(X86)}
  if ($null -eq $out) {
    $out = ${env:PROGRAMFILES}
  }

  if ($null -eq $out) {
    throw "Could not find [Program Files 32-bit]"
  }

  return $out
}

function getLatestVisualStudioWithDesktopWorkloadPath() {
  $programFiles = getProgramFiles32bit
  $vswhereExe = "$programFiles\Microsoft Visual Studio\Installer\vswhere.exe"
  if (Test-Path $vswhereExe) {
    $output = & $vswhereExe -products * -latest -requires Microsoft.VisualStudio.Workload.NativeDesktop -format xml
    [xml]$asXml = $output
    foreach ($instance in $asXml.instances.instance) {
      $installationPath = $instance.InstallationPath -replace "\\$" # Remove potential trailing backslash
    }
    if (!$installationPath) {
      Write-Host "Warning: no full Visual Studio setup has been found, extending search to include also partial installations" -ForegroundColor Yellow
      $output = & $vswhereExe -products * -latest -format xml
      [xml]$asXml = $output
      foreach ($instance in $asXml.instances.instance) {
        $installationPath = $instance.InstallationPath -replace "\\$" # Remove potential trailing backslash
      }
    }
    if (!$installationPath) {
      Throw "Could not locate any installation of Visual Studio"
    }
  }
  else {
    Throw "Could not locate vswhere at $vswhereExe"
  }
  return $installationPath
}


function getLatestVisualStudioWithDesktopWorkloadVersion() {
  $programFiles = getProgramFiles32bit
  $vswhereExe = "$programFiles\Microsoft Visual Studio\Installer\vswhere.exe"
  if (Test-Path $vswhereExe) {
    $output = & $vswhereExe -products * -latest -requires Microsoft.VisualStudio.Workload.NativeDesktop -format xml
    [xml]$asXml = $output
    foreach ($instance in $asXml.instances.instance) {
      $installationVersion = $instance.InstallationVersion
    }
    if (!$installationVersion) {
      Write-Host "Warning: no full Visual Studio setup has been found, extending search to include also partial installations" -ForegroundColor Yellow
      $output = & $vswhereExe -products * -latest -format xml
      [xml]$asXml = $output
      foreach ($instance in $asXml.instances.instance) {
        $installationVersion = $instance.installationVersion
      }
    }
    if (!$installationVersion) {
      Throw "Could not locate any installation of Visual Studio"
    }
  }
  else {
    Throw "Could not locate vswhere at $vswhereExe"
  }
  return $installationVersion
}


if ((Test-Path env:VCPKG_ROOT) -and $use_vcpkg) {
  $vcpkg_path = "$env:VCPKG_ROOT"
  Write-Host "Found vcpkg in VCPKG_ROOT: $vcpkg_path"
}
elseif ((Test-Path "${env:WORKSPACE}\vcpkg") -and $use_vcpkg) {
  $vcpkg_path = "${env:WORKSPACE}\vcpkg"
  $env:VCPKG_ROOT = "${env:WORKSPACE}\vcpkg"
  Write-Host "Found vcpkg in WORKSPACE\vcpkg: $vcpkg_path"
}
else {
  $use_vcpkg = $false
  Write-Host "Skipping vcpkg-enabled builds because the VCPKG_ROOT environment variable is not defined or you requested to avoid VCPKG, using self-distributed libs`n" -ForegroundColor Yellow
  $additional_build_setup = $additional_build_setup + " -DENABLE_VCPKG_INTEGRATION:BOOL=OFF"
}

if ($null -eq $env:VCPKG_DEFAULT_TRIPLET -and $use_vcpkg) {
  Write-Host "No default triplet has been set-up for vcpkg. Defaulting to x64-windows" -ForegroundColor Yellow
  $vcpkg_triplet = "x64-windows"
}
elseif ($use_vcpkg) {
  $vcpkg_triplet = $env:VCPKG_DEFAULT_TRIPLET
}

if ($vcpkg_triplet -Match "x86" -and $use_vcpkg) {
  Throw "darknet is supported only in x64 builds!"
}

if ($null -eq (Get-Command "cl.exe" -ErrorAction SilentlyContinue)) {
  $vsfound = getLatestVisualStudioWithDesktopWorkloadPath
  Write-Host "Found VS in ${vsfound}"
  Push-Location "${vsfound}\Common7\Tools"
  cmd.exe /c "VsDevCmd.bat -arch=x64 & set" |
  ForEach-Object {
    if ($_ -match "=") {
      $v = $_.split("="); Set-Item -force -path "ENV:\$($v[0])"  -value "$($v[1])"
    }
  }
  Pop-Location
  Write-Host "Visual Studio Command Prompt variables set" -ForegroundColor Yellow
}

$tokens = getLatestVisualStudioWithDesktopWorkloadVersion
$tokens = $tokens.split('.')
if ($use_ninja) {
  $generator = "Ninja"
}
else {
  if ($tokens[0] -eq "14") {
    $generator = "Visual Studio 14 2015"
  }
  elseif ($tokens[0] -eq "15") {
    $generator = "Visual Studio 15 2017"
  }
  elseif ($tokens[0] -eq "16") {
    $generator = "Visual Studio 16 2019"
  }
  else {
    throw "Unknown Visual Studio version, unsupported configuration"
  }
}
Write-Host "Setting up environment to use CMake generator: $generator" -ForegroundColor Yellow

if ($null -eq (Get-Command "nvcc.exe" -ErrorAction SilentlyContinue)) {
  if (Test-Path env:CUDA_PATH) {
    $env:PATH += ";${env:CUDA_PATH}\bin"
    Write-Host "Found cuda in ${env:CUDA_PATH}" -ForegroundColor Yellow
  }
  else {
    Write-Host "Unable to find CUDA, if necessary please install it or define a CUDA_PATH env variable pointing to the install folder" -ForegroundColor Yellow
  }
}

if (Test-Path env:CUDA_PATH) {
  if (-Not(Test-Path env:CUDA_TOOLKIT_ROOT_DIR)) {
    $env:CUDA_TOOLKIT_ROOT_DIR = "${env:CUDA_PATH}"
    Write-Host "Added missing env variable CUDA_TOOLKIT_ROOT_DIR" -ForegroundColor Yellow
  }
  if (-Not(Test-Path env:CUDACXX)) {
    $env:CUDACXX = "${env:CUDA_PATH}\bin\nvcc.exe"
    Write-Host "Added missing env variable CUDACXX" -ForegroundColor Yellow
  }
}

if ($force_cpp_build) {
  $additional_build_setup = $additional_build_setup + " -DBUILD_AS_CPP:BOOL=ON"
}

if (-Not($enable_cuda)) {
  $additional_build_setup = $additional_build_setup + " -DENABLE_CUDA:BOOL=OFF"
}

if ($use_vcpkg) {
  New-Item -Path .\build_win_release -ItemType directory -Force
  Set-Location build_win_release
  if ($use_ninja) {
    $cmake_args = "-G `"$generator`" `"-DVCPKG_TARGET_TRIPLET=$vcpkg_triplet`" `"-DCMAKE_BUILD_TYPE=Release`" ${additional_build_setup} -S .."
    $dllfolder = "."
  }
  else {
    $cmake_args = "-G `"$generator`" -T `"host=x64`" -A `"x64`" `"-DVCPKG_TARGET_TRIPLET=$vcpkg_triplet`" `"-DCMAKE_BUILD_TYPE=Release`" ${additional_build_setup} -S .."
    $dllfolder = "Release"
  }
}
else {
  # USE LOCAL PTHREAD LIB AND LOCAL STB HEADER, NO VCPKG, ONLY RELEASE MODE SUPPORTED
  # if you want to manually force this case, remove VCPKG_ROOT env variable and remember to use "vcpkg integrate remove" in case you had enabled user-wide vcpkg integration
  New-Item -Path .\build_win_release_novcpkg -ItemType directory -Force
  Set-Location build_win_release_novcpkg
  if ($use_ninja) {
    $cmake_args = "-G `"$generator`" ${additional_build_setup} -S .."
    $dllfolder = "..\3rdparty\pthreads\bin"
  }
  else {
    $cmake_args = "-G `"$generator`" -T `"host=x64`" -A `"x64`" ${additional_build_setup} -S .."
    $dllfolder = "..\3rdparty\pthreads\bin"
  }
}

Write-Host "CMake args: $cmake_args"
Start-Process -NoNewWindow -Wait -FilePath $CMAKE_EXE -ArgumentList $cmake_args
Start-Process -NoNewWindow -Wait -FilePath $CMAKE_EXE -ArgumentList "--build . --config Release --parallel ${number_of_build_workers} --target install"
Remove-Item DarknetConfig.cmake
Remove-Item DarknetConfigVersion.cmake
$dllfiles = Get-ChildItem ${dllfolder}\*.dll
if ($dllfiles) {
  Copy-Item $dllfiles ..
}
Set-Location ..
Copy-Item cmake\Modules\*.cmake share\darknet\
