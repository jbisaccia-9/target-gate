"""Azure Functions entry point (Python v2 model).

Timer: 06:00 UTC on the 1st and 15th - the twice-monthly cadence. The function
body is the same pipeline the CLI runs; Azure supplies the schedule, the Blob
container (via AZURE_STORAGE_CONNECTION_STRING), and the Graph credentials.
Deploy: `func azure functionapp publish <app-name>` with requirements-azure.txt.
"""
try:
    import azure.functions as func
except ImportError:                      # local clones without the azure extra
    func = None

import sys
sys.path.insert(0, "src")
from targetgate.pipeline import run      # noqa: E402

if func:
    app = func.FunctionApp()

    @app.timer_trigger(schedule="0 0 6 1,15 * *", arg_name="timer",
                       run_on_startup=False)
    def twice_monthly_targets(timer: func.TimerRequest) -> None:
        code = run(source="nppes")
        if code != 0:
            raise RuntimeError("target list failed the gate; delivery blocked")
