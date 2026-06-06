{% for version, sections in versions | dictsort(reverse=True) %}

{{ version }} ({{ project_date }})
{{ "=" * (version | length + project_date | length + 3) }}

{% for category, entries in sections | dictsort %}
{{ category }}
{{ "-" * (category | length) }}

{% for entry in entries %}
- {{ entry }}
{% endfor %}

{% endfor %}

{% endfor %}