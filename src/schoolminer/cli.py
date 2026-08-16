import re
from urllib.parse import urljoin

import httpx
import typer
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table

from schoolminer.config import CATEGORY_URL, INSPECTION_DIR, JHS_CATEGORY
from schoolminer.scraping.client import build_client
from schoolminer.sources.ghana_education_directory import (
    extract_antiforgery_token,
    fetch_search_page,
)

app = typer.Typer(
    help=(
        "Internal CLI for acquiring, cleaning, validating, and exporting "
        "Ghanaian school directory data."
    )
)

console = Console()


@app.callback()
def main() -> None:
    """Register subcommands under the root CLI."""


@app.command()
def hello() -> None:
    """Verify that School Miner is installed correctly."""

    console.print(
        "[bold green]EduSentrix School Miner is installed correctly and ready to use![/bold green]"
    )


@app.command("inspect")
def inspect_site(
    save_html: bool = typer.Option(
        True,
        "--save-html/--no-save-html",
        help="Save the returned category HTML for local inspection.",
    ),
    insecure: bool = typer.Option(
        False,
        "--insecure",
        help=("Disable TLS certificate verification for debugging against misconfigured sites."),
    ),
) -> None:
    """Inspect the JHS directory without scraping the full dataset."""

    console.rule("[bold blue]Ghana Education Directory Inspection[/bold blue]")

    console.print(f"Category: [cyan]{JHS_CATEGORY}[/cyan]")
    console.print(f"Endpoint: [cyan]{CATEGORY_URL}[/cyan]")

    tls_mode = "[yellow]DISABLED[/yellow]" if insecure else "[green]ENABLED[/green]"

    console.print(f"TLS verification: {tls_mode}")
    console.print()

    if insecure:
        console.print(
            "[bold yellow]WARNING: TLS certificate verification is disabled.[/bold yellow]"
        )
        console.print(
            "[yellow]"
            "This should only be used for this source while its TLS "
            "certificate is misconfigured or expired."
            "[/yellow]"
        )
        console.print()

    try:
        with build_client(verify=not insecure) as client:
            response = client.get(
                CATEGORY_URL,
                params={"c": JHS_CATEGORY},
            )

            response.raise_for_status()

    except httpx.RequestError as exc:
        console.print(f"[bold red]Network error while requesting {exc.request.url}[/bold red]")
        console.print(str(exc))

        raise typer.Exit(code=1) from exc

    except httpx.HTTPStatusError as exc:
        console.print(
            f"[bold red]HTTP {exc.response.status_code} returned by {exc.request.url}[/bold red]"
        )

        raise typer.Exit(code=1) from exc

    soup = BeautifulSoup(response.text, "lxml")

    title = soup.title.get_text(" ", strip=True) if soup.title else "(no title)"

    page_text = soup.get_text(" ", strip=True)

    listing_match = re.search(
        r"Showing\s+(\d+)\s+of\s+([\d,]+)\s+Listings",
        page_text,
        re.IGNORECASE,
    )

    page_match = re.search(
        r"Page\s+(\d+)\s+of\s+([\d,]+)",
        page_text,
        re.IGNORECASE,
    )

    detail_links: list[str] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")

        if href and "/Search/Details/" in href:
            full_url = urljoin(
                str(response.url),
                href,
            )

            detail_links.append(full_url)

    detail_links = list(dict.fromkeys(detail_links))

    console.print("[bold]Response[/bold]")

    console.print(f"Status: [green]{response.status_code}[/green]")

    console.print(f"Final URL: {response.url}")

    console.print(f"Content-Type: {response.headers.get('content-type', '(missing)')}")

    console.print(f"HTML characters: {len(response.text):,}")

    console.print(f"Page title: {title}")

    console.print()

    console.print("[bold]Directory summary[/bold]")

    if listing_match:
        visible_count = int(listing_match.group(1))

        total_count = int(listing_match.group(2).replace(",", ""))

        console.print(f"Listings visible: {visible_count:,}")

        console.print(f"Total listings reported: {total_count:,}")

    else:
        console.print("[yellow]Could not detect listing count text.[/yellow]")

    if page_match:
        current_page = int(page_match.group(1))

        total_pages = int(page_match.group(2).replace(",", ""))

        console.print(f"Current page: {current_page:,}")

        console.print(f"Total pages reported: {total_pages:,}")

    else:
        console.print("[yellow]Could not detect page count text.[/yellow]")

    console.print(f"Detail links found in HTML: {len(detail_links):,}")

    console.print()

    if detail_links:
        table = Table(title="School detail links found")

        table.add_column(
            "#",
            justify="right",
        )

        table.add_column("URL")

        for index, detail_url in enumerate(
            detail_links,
            start=1,
        ):
            table.add_row(
                str(index),
                detail_url,
            )

        console.print(table)

    selects = soup.find_all("select")

    console.print()

    console.print(f"[bold]Select/dropdown elements found:[/bold] {len(selects)}")

    for index, select in enumerate(
        selects,
        start=1,
    ):
        console.print()

        console.print(
            f"[bold]Select {index}[/bold] name={select.get('name')!r} id={select.get('id')!r}"
        )

        options = select.find_all("option")

        for option in options:
            label = option.get_text(
                " ",
                strip=True,
            )

            value = option.get("value")

            console.print(f"  • {label!r} -> value={value!r}")

    if save_html:
        INSPECTION_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = INSPECTION_DIR / "jhs-category.html"

        output_path.write_text(
            response.text,
            encoding="utf-8",
        )

        console.print()

        console.print(f"[green]Saved raw HTML to {output_path}[/green]")


@app.command("inspect-api")
def inspect_api(
    page: int = typer.Option(
        2,
        "--page",
        min=1,
        help="Search results page to inspect.",
    ),
    region: str = typer.Option(
        "All",
        "--region",
        help="Region filter value sent to the directory.",
    ),
    insecure: bool = typer.Option(
        False,
        "--insecure",
        help=("Disable TLS certificate verification for debugging against misconfigured sites."),
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Print additional request and response diagnostics.",
    ),
) -> None:
    """Inspect the directory's structured search endpoint."""

    console.rule("[bold blue]Ghana Education Directory API Inspection[/bold blue]")

    console.print(f"Page: [cyan]{page}[/cyan]")
    console.print(f"Region: [cyan]{region}[/cyan]")
    console.print()
    if insecure:
        console.print(
            "[bold yellow]WARNING: TLS certificate verification is disabled.[/bold yellow]"
        )
        console.print()
    try:
        with build_client(verify=not insecure) as client:
            category_response = client.get(
                CATEGORY_URL,
                params={"c": JHS_CATEGORY},
            )
            category_response.raise_for_status()

            token = extract_antiforgery_token(category_response.text)
            console.print("[green]Anti-forgery token extracted successfully[/green]")
            console.print(f"Token length: {len(token)} characters")

            search_response = fetch_search_page(
                client,
                token=token,
                page=page,
                region=region,
            )
            search_response.raise_for_status()

            if debug:
                console.print()
                console.print("[bold]Request diagnostics[/bold]")

                console.print(f"Method: {search_response.request.method}")

                console.print(f"URL: {search_response.request.url}")

                content_type = search_response.request.headers.get(
                    "content-type",
                    "(missing)",
                )

                console.print(f"Content-Type: {content_type}")

    except httpx.RequestError as exc:
        console.print(f"[bold red]Network error while requesting {exc.request.url}[/bold red]")
        console.print(str(exc))

        raise typer.Exit(code=1) from exc

    except httpx.HTTPStatusError as exc:
        console.print(
            f"[bold red]HTTP {exc.response.status_code} returned by {exc.request.url}[/bold red]"
        )
        console.print(exc.response.text[:1000])

        raise typer.Exit(code=1) from exc

    except ValueError as exc:
        console.print(f"[bold red]{exc}[/bold red]")

        raise typer.Exit(code=1) from exc

    console.print()
    console.print("[bold]Search response[/bold]")

    console.print(f"Status: [green]{search_response.status_code}[/green]")
    console.print(f"Final URL: {search_response.url}")

    console.print(f"Response characters: {len(search_response.text):,}")
    console.print()

    try:
        payload = search_response.json()
    except ValueError as exc:
        console.print("[bold red]Search endpoint did not return valid JSON[/bold red]")

        console.print()
        console.print(search_response.text[:2000])

        raise typer.Exit(code=1) from exc

    console.print("[green]Valid JSON response received.[/green]")

    if not isinstance(payload, dict):
        console.print(f"[yellow]Expected a JSON object, got {type(payload).__name__}.[/yellow]")
        raise typer.Exit(code=1)

    console.print(f"Top-level keys: {list(payload.keys())}")

    page_count = payload.get("PageCount")
    records = payload.get("Data")

    console.print(f"PageCount: {page_count!r}")

    if isinstance(records, list):
        console.print(f"Records returned: {len(records)}")

        if records:
            console.print()

            table = Table(title=f"Search results - page {page}")

            table.add_column(
                "ID",
                justify="right",
            )
            table.add_column("School")
            table.add_column("Region")
            table.add_column("Town")
            table.add_column("Phone")
            table.add_column("Ownership")

            for record in records:
                ownership_id = record.get("OwnerShipId")

                if ownership_id == 1:
                    ownership = "Private"
                elif ownership_id == 2:
                    ownership = "Public"
                else:
                    ownership = str(ownership_id)

                table.add_row(
                    str(record.get("InstitutionId", "")),
                    str(record.get("InstitutionName", "")),
                    str(record.get("Region", "")),
                    str(record.get("TownName", "")),
                    str(record.get("Phone", "")),
                    ownership,
                )

            console.print(table)

            console.print()
            console.print("[bold]Raw fields in first record[/bold]")

            first_record = records[0]

            for key, value in first_record.items():
                console.print(f"{key}: {value!r}")
    else:
        console.print("[yellow]Data is not a list or is missing.[/yellow]")


if __name__ == "__main__":
    app()
