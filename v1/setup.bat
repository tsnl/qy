@ECHO OFF

REM: For VM
REM @CD qcl\vm\
REM @python3.9 setup.py build_ext --inplace --plat-name=win-amd64
REM @CD ..\..\

REM: for `monomorphizer`
CD qcl\monomorphizer\
cmake -DCMAKE_BUILD_TYPE=Release .
cmake --build . --config Release
python setup.py build_ext --inplace
CD ..\..\
