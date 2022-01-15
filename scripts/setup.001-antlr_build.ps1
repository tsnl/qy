Set-Variable -Name NAMESPACE -Value "q4"
Set-Variable -Name GRAMMAR_RELPATH -Value ".\grammars\Q4SourceFile.g4"
Set-Variable -Name CORRECT_CWD_TOKEN -Value "correct-cwd-token-48018.txt"
Set-Variable -Name ANTLR_SOURCE_TEST_FILE_PATH -Value "dev\antlr4-cpp-runtime\source\CMakeLists.txt"
Set-Variable -Name ANTLR_BUILD_TEST_FILE_PATH -Value "dev\antlr4-cpp-runtime\build\cmake_install.cmake"

if (-not (Test-Path -Path .\${CORRECT_CWD_TOKEN} -PathType Leaf)) {
    Write-Host "ERROR:  Could not locate correct current-working-directory token named '${CORRECT_CWD_TOKEN}'."
    Write-Host "        Please run this script from that directory instead."
    exit 1
}

if (($args.Count -gt 0) -and ("clean" -in $args)) {
    Write-Host "INFO:   Cleaning..."
    Remove-Item -Force -Recurse ".\dev\antlr4-cpp-runtime\*" -Confirm:$false
    Remove-Item -Force ".\dev\antlr4-cpp-runtime" -Confirm:$false
}

if (-not (Test-Path -Path .\${ANTLR_SOURCE_TEST_FILE_PATH})) {
    mkdir -Path dev\antlr4-cpp-runtime\source -Force -ErrorAction SilentlyContinue
    Expand-Archive -Path .\dev\antlr4-cpp-runtime-4.9.3-source.zip -DestinationPath .\dev\antlr4-cpp-runtime\source\ -Force
}

if (-not (Test-Path -Path .\${ANTLR_BUILD_TEST_FILE_PATH})) {
    mkdir -Path dev\antlr4-cpp-runtime\build -Force -ErrorAction SilentlyContinue
    mkdir -Path dev\antlr4-cpp-runtime\install -Force -ErrorAction SilentlyContinue
    Push-Location -Path dev\antlr4-cpp-runtime\build\
        cmake.exe ..\source -DCMAKE_BUILD_TYPE=RelWithDebInfo
        cmake.exe --build . --parallel $((Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors)
        cmake.exe --build .     # in case of clock skew
    Pop-Location
}

Write-Host "INFO:   Generating ANTLR output"
java.exe -jar "dev\antlr-4.9.3-complete.jar" $(Resolve-Path ${GRAMMAR_RELPATH}) -no-listener -visitor -o gen/ -package ${NAMESPACE}

exit 0
