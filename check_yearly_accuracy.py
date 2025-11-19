"""Check accuracy of interpreted yearly forecast against raw data."""
import json
from api.services.forecast_builders import yearly_payload

# Load test request
with open('test_yearly_forecast_story.json', 'r') as f:
    data = json.load(f)

# Get raw yearly forecast
print("Generating raw forecast...")
raw_forecast = yearly_payload(data['chart_input'], data['options'])

# Count raw events
raw_total = 0
raw_by_month = {}
for month, events in raw_forecast.get('months', {}).items():
    count = len(events)
    raw_by_month[month] = count
    raw_total += count

print('\n=== RAW vs INTERPRETED COMPARISON ===\n')
print('RAW FORECAST DATA:')
print(f'  Total events (all months): {raw_total}')
print(f'  Top events: {len(raw_forecast.get("top_events", []))}')
print(f'  Months: {len(raw_forecast.get("months", {}))}')
print()

# Load interpreted response
with open('response_yearly_story.json', 'r', encoding='utf-8-sig') as f:
    response = json.load(f)

report = response['report']
print('INTERPRETED REPORT:')
print(f'  Total events (appendix): {len(report["appendix_all_events"])}')
print(f'  Top events: {len(report["year_at_glance"]["top_events"])}')
print(f'  Months: {len(report["months"])}')
print()

# Event count match check
print('EVENT COUNT VERIFICATION:')
if raw_total == len(report['appendix_all_events']):
    print(f'  [OK] Event counts match: {raw_total} events')
else:
    diff = abs(raw_total - len(report['appendix_all_events']))
    print(f'  [WARN] Mismatch: Raw={raw_total}, Interpreted={len(report["appendix_all_events"])} (diff: {diff})')
print()

# Monthly breakdown
print('MONTHLY EVENT BREAKDOWN:')
print(f'{"Month":12} {"Raw":>6} {"Interpreted":>12}  {"Status":>8}')
print('-' * 45)
for month in sorted(raw_by_month.keys()):
    raw_count = raw_by_month[month]
    # Find matching month in report
    interp_month = next((m for m in report['months'] if m['month'] == month), None)
    if interp_month:
        # Count from aspect_grid since it contains all events for that month
        interp_count = len(interp_month['aspect_grid'])
        match = '[OK]' if abs(raw_count - interp_count) <= 2 else '[WARN]'
        print(f'{month:12} {raw_count:6} {interp_count:12}  {match:>8}')
    else:
        print(f'{month:12} {raw_count:6} {"N/A":>12}  {"[ERROR]":>8}')
print()

# Sample event comparison
print('SAMPLE EVENT COMPARISON (First Event):')
if raw_forecast.get('months'):
    first_month_key = list(raw_forecast.get('months', {}).keys())[0]
    raw_sample = raw_forecast['months'][first_month_key][0]
    interp_sample = report['appendix_all_events'][0]

    print('  Raw Event:')
    print(f'    Date: {raw_sample.get("date")}')
    print(f'    Transit: {raw_sample.get("transit_body")}')
    print(f'    Natal: {raw_sample.get("natal_body")}')
    print(f'    Aspect: {raw_sample.get("aspect")}')
    print(f'    Score: {raw_sample.get("score")}')
    print(f'    Note: {raw_sample.get("note", "")[:80]}...')
    print()
    print('  Interpreted Event:')
    print(f'    Date: {interp_sample.get("date")}')
    print(f'    Transit: {interp_sample.get("transit_body")}')
    print(f'    Natal: {interp_sample.get("natal_body")}')
    print(f'    Aspect: {interp_sample.get("aspect")}')
    print(f'    Score: {interp_sample.get("score")}')
    print(f'    Theme: {interp_sample.get("section")}')
    print(f'    Summary: {interp_sample.get("user_friendly_summary", "")[:80]}...')
    print()

    # Check if data matches
    matches = []
    matches.append(('Date', raw_sample.get('date') == interp_sample.get('date')))
    matches.append(('Transit', raw_sample.get('transit_body') == interp_sample.get('transit_body')))
    matches.append(('Natal', raw_sample.get('natal_body') == interp_sample.get('natal_body')))
    matches.append(('Aspect', raw_sample.get('aspect') == interp_sample.get('aspect')))
    matches.append(('Score', abs(float(raw_sample.get('score', 0)) - float(interp_sample.get('score', 0))) < 0.01))

    print('  Field-by-Field Match:')
    for field, match in matches:
        status = '[OK]' if match else '[FAIL]'
        print(f'    {field:10}: {status}')
    print()

    all_match = all(m[1] for m in matches)
    if all_match:
        print('  [OK] Event data matches perfectly!')
    else:
        print('  [WARN] Some event fields do not match')

print('\n=== COMPARISON COMPLETE ===\n')

# Additional checks
print('ADDITIONAL VALIDATION:')

# Check that all events have themes assigned
events_without_theme = [e for e in report['appendix_all_events'] if not e.get('section')]
if events_without_theme:
    print(f'  [WARN] {len(events_without_theme)} events without theme assigned')
else:
    print(f'  [OK] All events have themes assigned')

# Check that summaries are populated
events_without_summary = [e for e in report['appendix_all_events'] if not e.get('user_friendly_summary')]
if events_without_summary:
    print(f'  [WARN] {len(events_without_summary)} events without summary')
else:
    print(f'  [OK] All events have summaries')

# Check narrative content
empty_narratives = []
for month in report['months']:
    if len(month.get('overview', '')) < 50:
        empty_narratives.append(f"{month['month']}/overview")
    if len(month.get('career_and_finance', '')) < 50:
        empty_narratives.append(f"{month['month']}/career")
    if len(month.get('relationships_and_family', '')) < 50:
        empty_narratives.append(f"{month['month']}/relationships")
    if len(month.get('health_and_energy', '')) < 50:
        empty_narratives.append(f"{month['month']}/health")

if empty_narratives:
    print(f'  [WARN] {len(empty_narratives)} narrative sections are too short or empty')
    for section in empty_narratives[:5]:
        print(f'    - {section}')
else:
    print(f'  [OK] All narrative sections have substantial content')

# Check year commentary
year_commentary = report['year_at_glance'].get('commentary', '')
if len(year_commentary) < 100:
    print(f'  [WARN] Year commentary is too short ({len(year_commentary)} chars)')
else:
    print(f'  [OK] Year commentary has {len(year_commentary)} characters')

print('\n=== ALL CHECKS COMPLETE ===')

