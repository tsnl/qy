@ECHO OFF

SET ANTLR=java -jar .\dev\antlr-4.9.2-complete.jar
SET GFILE=.\NativeQyModule.g4

@ECHO Running ANTLR4...
@ECHO ON
    @%ANTLR% %GFILE% -o .\qcl\parser\gen\ -no-listener -visitor
@ECHO OFF
@ECHO Done.
