"""
deadletter CLI -- interact with the URL shortener from the terminal.

Usage examples:
    python cli.py shorten --url https://example.com --title "Example" --user 1
    python cli.py redirect HOE5Es
    python cli.py inspect HOE5Es
    python cli.py list --active
    python cli.py delete HOE5Es --reason user_requested
    python cli.py events --url HOE5Es
    python cli.py dashboard
    python cli.py health
    python cli.py metrics
"""
import os
import time
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

try:
    import httpx
    _HTTP = httpx
except ImportError:
    import urllib.request
    import json as _json
    _HTTP = None

import json
import urllib.request
import urllib.error

app = typer.Typer(help='deadletter URL shortener CLI')
console = Console()

_BASE = os.getenv('API_URL', 'http://localhost:5000')


def _get(path: str):
    url = f'{_BASE}{path}'
    try:
        with urllib.request.urlopen(url) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _post(path: str, body: dict):
    url = f'{_BASE}{path}'
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data,
                                  headers={'Content-Type': 'application/json'},
                                  method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _put(path: str, body: dict):
    url = f'{_BASE}{path}'
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data,
                                  headers={'Content-Type': 'application/json'},
                                  method='PUT')
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _delete(path: str, body: dict):
    url = f'{_BASE}{path}'
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data,
                                  headers={'Content-Type': 'application/json'},
                                  method='DELETE')
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _event_color(event_type: str) -> str:
    return {'created': 'green', 'updated': 'yellow', 'deleted': 'red'}.get(event_type, 'white')


def _status_text(is_active: bool) -> Text:
    if is_active:
        return Text('active', style='bold green')
    return Text('inactive', style='dim red strike')


@app.command()
def shorten(
    url: str = typer.Option(..., '--url', help='URL to shorten (must start with http/https)'),
    title: str = typer.Option(..., '--title', help='Human-readable title'),
    user: int = typer.Option(..., '--user', help='User ID'),
):
    """Shorten a URL."""
    status, data = _post('/urls', {'original_url': url, 'title': title, 'user_id': user})
    if status != 201:
        rprint(f'[red]Error {status}:[/red] {data.get("detail", data)}')
        raise typer.Exit(1)
    rprint(f'[green]Created:[/green] [bold]{data["short_code"]}[/bold]  ->  {data["original_url"]}')
    rprint(f'Redirect: {_BASE}/r/{data["short_code"]}')


@app.command()
def redirect(short_code: str = typer.Argument(..., help='Short code to look up')):
    """Show what a short code redirects to (or 404 if inactive/missing)."""
    status, data = _get(f'/urls/{short_code}')
    if status == 404:
        rprint(f'[red]404:[/red] {data.get("detail")}')
        raise typer.Exit(1)
    if not data['is_active']:
        rprint(f'[dim red strike]{short_code}[/dim red strike] is inactive -- would return 404')
        raise typer.Exit(1)
    rprint(f'[green]302 Redirect:[/green] {data["original_url"]}')


@app.command()
def inspect(short_code: str = typer.Argument(..., help='Short code to inspect')):
    """Show URL details and full event history."""
    status, data = _get(f'/urls/{short_code}')
    if status == 404:
        rprint(f'[red]404:[/red] {data.get("detail")}')
        raise typer.Exit(1)

    panel_text = (
        f'[bold]Short code:[/bold] {data["short_code"]}\n'
        f'[bold]Original URL:[/bold] {data["original_url"]}\n'
        f'[bold]Title:[/bold] {data["title"]}\n'
        f'[bold]Status:[/bold] {_status_text(data["is_active"])}\n'
        f'[bold]Created:[/bold] {data["created_at"]}\n'
        f'[bold]Updated:[/bold] {data["updated_at"]}'
    )
    console.print(Panel(panel_text, title=f'URL: {short_code}', border_style='blue'))

    events = data.get('events', [])
    if not events:
        rprint('[dim]No events.[/dim]')
        return

    table = Table(title='Event History', show_header=True)
    table.add_column('ID', style='dim', width=6)
    table.add_column('Type', width=10)
    table.add_column('Timestamp', width=22)
    table.add_column('Details')

    for e in events:
        color = _event_color(e['event_type'])
        details_str = json.dumps(e['details'], indent=2)
        table.add_row(
            str(e['id']),
            Text(e['event_type'], style=color),
            e['timestamp'],
            Syntax(details_str, 'json', theme='monokai', word_wrap=True),
        )
    console.print(table)


@app.command(name='list')
def list_urls(
    active: bool = typer.Option(False, '--active', is_flag=True, help='Show only active URLs'),
    inactive: bool = typer.Option(False, '--inactive', is_flag=True, help='Show only inactive URLs'),
    user_id: Optional[int] = typer.Option(None, '--user', help='Filter by user ID'),
):
    """List URLs."""
    params = []
    if active:
        params.append('is_active=true')
    elif inactive:
        params.append('is_active=false')
    if user_id:
        params.append(f'user_id={user_id}')
    qs = '?' + '&'.join(params) if params else ''

    status, data = _get(f'/urls{qs}')
    if status != 200:
        rprint(f'[red]Error {status}[/red]')
        raise typer.Exit(1)

    table = Table(title=f'URLs ({len(data)} total)', show_header=True)
    table.add_column('Short Code', style='bold cyan', width=10)
    table.add_column('Title', width=30)
    table.add_column('Original URL', width=50)
    table.add_column('Status', width=10)
    table.add_column('Created', width=20)

    for u in data:
        table.add_row(
            u['short_code'],
            u['title'],
            u['original_url'],
            _status_text(u['is_active']),
            u['created_at'][:19],
        )
    console.print(table)


@app.command()
def delete(
    short_code: str = typer.Argument(...),
    reason: str = typer.Option('user_requested', '--reason',
                                help='policy_cleanup | user_requested | duplicate'),
):
    """Soft-delete a URL (sets is_active=False)."""
    status, data = _delete(f'/urls/{short_code}', {'reason': reason})
    if status == 200:
        rprint(f'[yellow]Deleted:[/yellow] {short_code} (reason: {reason})')
    elif status == 409:
        rprint(f'[dim]Already inactive:[/dim] {short_code}')
    else:
        rprint(f'[red]Error {status}:[/red] {data.get("detail", data)}')
        raise typer.Exit(1)


@app.command()
def events(
    url: Optional[str] = typer.Option(None, '--url', help='Filter by short code'),
    event_type: Optional[str] = typer.Option(None, '--type', help='created | updated | deleted'),
):
    """List events."""
    params = []
    if url:
        params.append(f'short_code={url}')
    if event_type:
        params.append(f'event_type={event_type}')
    qs = '?' + '&'.join(params) if params else ''

    status, data = _get(f'/events{qs}')
    if status != 200:
        rprint(f'[red]Error {status}[/red]')
        raise typer.Exit(1)

    table = Table(title=f'Events ({len(data)} total)', show_header=True)
    table.add_column('ID', style='dim', width=6)
    table.add_column('URL ID', width=8)
    table.add_column('Type', width=10)
    table.add_column('Timestamp', width=22)
    table.add_column('Details')

    for e in data:
        color = _event_color(e['event_type'])
        table.add_row(
            str(e['id']),
            str(e['url_id']),
            Text(e['event_type'], style=color),
            e['timestamp'][:19],
            json.dumps(e['details']),
        )
    console.print(table)


@app.command()
def health():
    """Check API health."""
    status, data = _get('/health')
    if status == 200:
        rprint(f'[green]OK[/green] -- {data}')
    else:
        rprint(f'[red]UNHEALTHY[/red] {status}')
        raise typer.Exit(1)


@app.command()
def metrics():
    """Show API metrics."""
    status, data = _get('/metrics')
    if status != 200:
        rprint(f'[red]Error {status}[/red]')
        raise typer.Exit(1)

    table = Table(title='Metrics', show_header=False)
    table.add_column('Key', style='bold cyan')
    table.add_column('Value')
    for k, v in data.items():
        table.add_row(k, str(v))
    console.print(table)


@app.command()
def dashboard():
    """Live dashboard: URL stats + recent events."""
    def _build():
        _, m = _get('/metrics')
        _, ev = _get('/events')
        _, urls = _get('/urls')

        layout = Layout()
        layout.split_column(
            Layout(name='top', size=12),
            Layout(name='bottom'),
        )
        layout['top'].split_row(
            Layout(name='stats'),
            Layout(name='recent_events'),
        )

        stats_text = (
            f'Total URLs:    [bold]{m.get("urls_total", "?")}[/bold]\n'
            f'Active:        [green]{m.get("urls_active", "?")}[/green]\n'
            f'Inactive:      [dim red]{m.get("urls_inactive", "?")}[/dim red]\n'
            f'Total events:  [bold]{m.get("events_total", "?")}[/bold]\n'
            f'CPU:           {m.get("cpu_percent", "?")}%\n'
            f'Memory:        {m.get("memory_used_mb", "?")} / {m.get("memory_total_mb", "?")} MB\n'
            f'Uptime:        {m.get("uptime_seconds", "?")}s'
        )
        layout['stats'].update(Panel(stats_text, title='Stats', border_style='blue'))

        ev_table = Table(show_header=True, box=None)
        ev_table.add_column('Type', width=10)
        ev_table.add_column('URL ID', width=8)
        ev_table.add_column('Time', width=20)
        for e in (ev or [])[:10]:
            color = _event_color(e['event_type'])
            ev_table.add_row(
                Text(e['event_type'], style=color),
                str(e['url_id']),
                e['timestamp'][:19],
            )
        layout['recent_events'].update(Panel(ev_table, title='Recent Events', border_style='yellow'))

        log_table = Table(show_header=True, box=None)
        log_table.add_column('Short Code', style='cyan', width=10)
        log_table.add_column('Title', width=30)
        log_table.add_column('Status', width=10)
        log_table.add_column('URL')
        for u in (urls or [])[:15]:
            log_table.add_row(
                u['short_code'],
                u['title'],
                _status_text(u['is_active']),
                u['original_url'],
            )
        layout['bottom'].update(Panel(log_table, title='Recent URLs', border_style='green'))
        return layout

    rprint('[dim]Live dashboard -- Ctrl+C to exit[/dim]')
    with Live(console=console, refresh_per_second=1, screen=True) as live:
        while True:
            try:
                live.update(_build())
                time.sleep(5)
            except KeyboardInterrupt:
                break


if __name__ == '__main__':
    app()
