@echo off 

if /i "%1"=="dotnet" call GetDotNetLang
echo de-DE 


:: http://msdn.microsoft.com/en-us/library/ee825488%28CS.20%29.aspx

:GetDotNetLang
if /i "%1"==DEU echo de-DE
if /i "%1"==FRA echo fr-FR
if /i "%1"==ITA echo it-IT
if /i "%1"==ESP echo es-ES

if /i "%1"==JPN echo ja-JP
if /i "%1"==KOR echo ko-KR
if /i "%1"==CHT echo cn-TW
if /i "%1"==CHS echo cn-ZH

if /i "%1"==CSY echo cs-CZ
if /i "%1"==PLK echo pl-PL
if /i "%1"==HUN echo hu-HU
if /i "%1"==RUS echo ru-RU

if /i "%1"==FIN echo fi-FI
if /i "%1"==PTB echo pt-BR
if /i "%1"==VIT echo vi-VN


goto EOF
