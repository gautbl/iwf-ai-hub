@echo off
REM Exécute les tests avec -W error, en ignorant les avertissements amont
REM inoffensifs que pytest ne peut pas filtrer via filterwarnings (LIFO).
REM
REM Usage : scripts\run_tests.bat [options pytest suppl.]
REM
REM Voir .scratch/hardening-ship/issues/04-warnings-and-tooling.md
REM pour le contexte du contournement.

.venv\Scripts\python.exe -m pytest ^
    -W error ^
    -W "ignore::PendingDeprecationWarning:langgraph" ^
    -W "ignore::DeprecationWarning:starlette.testclient" ^
    %*