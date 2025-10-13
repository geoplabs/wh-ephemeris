# Forecast Report Storage & Download URLs

The forecast PDF generator writes output either to local storage (for development)
or to S3 (for shared environments). Download links are resolved through
`api/services/forecast_reports.py` using the following priority:

1. **`REPORTS_BASE_URL`** – when this environment variable is set, it is used verbatim
   for every generated report. Point this to whichever host is configured to expose
the PDF objects (for example, `https://cdn.whathoroscope.com` when a CDN fronts the
   bucket, or `https://api.whathoroscope.com` when the API service proxies the
   downloads).
2. **Presigned URLs** – if S3 is enabled and no base URL is configured, the service
   attempts to mint a presigned link to the uploaded object.
3. **Environment fallback** – when neither of the above paths succeeds, the code
   falls back to `https://api.whathoroscope.com/…` for production-like environments
   and `/dev-assets/…` during local development.

Because the first step is entirely configuration-driven, choose the domain that is
reachable in your deployment. Production can continue using
`https://api.whathoroscope.com` by default, while staging or future CDN rollouts can
switch to `https://cdn.whathoroscope.com` simply by updating `REPORTS_BASE_URL`.
