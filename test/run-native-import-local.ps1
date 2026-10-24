param([string]$Script = '/work/test/native-file-import-integration.py', [string[]]$ScriptArgs = @())
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$info = docker inspect farmer-registry-celery-worker | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Running farmer worker required for local environment settings' }
$dockerArgs = @('run','--rm','--network','farmer-registry_default',
    '--add-host','keycloak.localtest.me:host-gateway','--add-host','platform.localtest.me:host-gateway',
    '-v', ($root + ':/work'), '--entrypoint','python')
foreach ($hostEntry in $info.HostConfig.ExtraHosts) { $dockerArgs += @('--add-host',$hostEntry) }
foreach ($entry in $info.Config.Env) {
    if ($entry -notmatch '^(PATH|PYTHONPATH|REGISTRY_CELERY_WORKERS_DB_DBNAME|REGISTRY_CELERY_WORKERS_IMPORT_FILE_SENDER_ID|REGISTRY_CELERY_WORKERS_AWE_TOKEN_URL|REGISTRY_CELERY_WORKERS_AWE_ENABLED|REGISTRY_CORE_AWE_ENABLED|REGISTRY_CELERY_WORKERS_CELERY_BROKER_URL|REGISTRY_CELERY_WORKERS_CELERY_BACKEND_URL)=') {
        $dockerArgs += @('-e',$entry)
    }
}
# No worker or beat is started; real tasks run synchronously against an isolated DB.
$dockerArgs += @('-e','PYTHONPATH=/work/farmer-extension/src',
    '-e','REGISTRY_CELERY_WORKERS_DB_DBNAME=farmer_native_import_test',
    '-e','REGISTRY_CELERY_WORKERS_IMPORT_FILE_SENDER_ID=farmer-partner',
    '-e','REGISTRY_CELERY_WORKERS_AWE_ENABLED=false','-e','REGISTRY_CORE_AWE_ENABLED=false',
    '-e','REGISTRY_CELERY_WORKERS_CELERY_BROKER_URL=memory://',
    '-e','REGISTRY_CELERY_WORKERS_CELERY_BACKEND_URL=cache+memory://',
    'farmer-registry-local/native-import-celery:dev',$Script)
$dockerArgs += $ScriptArgs
$ErrorActionPreference = 'Continue'
& docker @dockerArgs
exit $LASTEXITCODE
