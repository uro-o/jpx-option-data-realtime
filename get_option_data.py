Run python get_option_data.py
Traceback (most recent call last):

========================================
JPX OPTION DATA
========================================
Collected at: 2026-08-19T14:49:32+09:00
========================================
Initializing QRI session...
Initial access: 503
  File "/home/runner/work/jpx-option-data-realtime/jpx-option-data-realtime/get_option_data.py", line 1129, in <module>
    main()
  File "/home/runner/work/jpx-option-data-realtime/jpx-option-data-realtime/get_option_data.py", line 946, in main
    initialize_session()
  File "/home/runner/work/jpx-option-data-realtime/jpx-option-data-realtime/get_option_data.py", line 214, in initialize_session
    response.raise_for_status()
  File "/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/requests/models.py", line 1167, in raise_for_status
    raise HTTPError(http_error_msg, response=self)
requests.exceptions.HTTPError: 503 Server Error: Service Unavailable for url: https://svc.qri.jp/
Error: Process completed with exit code 1.
