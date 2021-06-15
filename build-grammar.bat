@ECHO OFF

SET ANTLR=java -jar .\dev\antlr-4.9.2-complete.jar
SET GFILE=.\NativeQyModule.g4

@ECHO Running ANTLR4...
@%ANTLR% %GFILE% -o .\qcl\antlr\gen\ -no-listener -visitor
@ECHO Done.
