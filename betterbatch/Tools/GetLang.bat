@echo off 

if (%1)==() goto NO_TYPE
if "%2"=="" goto NO_LANG

if /i "%1"=="dotnet" goto GetDotNetLang


:: http://msdn.microsoft.com/en-us/library/ee825488%28CS.20%29.aspx

:GetDotNetLang
if /i %2==DEU set __dot_net_lang=de-DE
if /i %2==FRA set __dot_net_lang=fr-FR
if /i %2==ITA set __dot_net_lang=it-IT
if /i %2==ESP set __dot_net_lang=es-ES

if /i %2==JPN set __dot_net_lang=ja-JP
if /i %2==KOR set __dot_net_lang=ko-KR
if /i %2==CHT set __dot_net_lang=cn-TW
if /i %2==CHS set __dot_net_lang=cn-ZH

if /i %2==CSY set __dot_net_lang=cs-CZ
if /i %2==PLK set __dot_net_lang=pl-PL
if /i %2==HUN set __dot_net_lang=hu-HU
if /i %2==RUS set __dot_net_lang=ru-RU

if /i %2==FIN set __dot_net_lang=fi-FI
if /i %2==PTB set __dot_net_lang=pt-BR
if /i %2==VIT set __dot_net_lang=vi-VN

if %__dot_net_lang%_==_ goto UnknownLanguage
echo %__dot_net_lang%
set __dot_net_lang=
goto Success_EXIT

:NO_TYPE
echo Language Type not specified (e.g. dotnet)
goto FAILURE_EXIT

:NO_LANG
echo Language not specified (e.g. deu, Fra, etc)
goto FAILURE_EXIT

:UnknownLanguage
echo Language %2 is not a known language
goto FAILURE_EXIT

:FAILURE_EXIT
exit /B 1

:Success_EXIT
exit /B 0
