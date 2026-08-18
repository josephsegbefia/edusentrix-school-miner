from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin

import httpx
import typer
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table

from schoolminer.config import (
    CATEGORY_URL,
    INSPECTION_DIR,
    JHS_CATEGORY,
    RAW_DIR,
    STATE_DB_PATH,
)
from schoolminer.scraping.client import build_client
from schoolminer.scraping.crawler import (
    create_directory_crawl,
    run_directory_crawl,
)
from schoolminer.sources.ghana_education_directory import (
    extract_antiforgery_token,
    fetch_search_page,
    parse_search_response,
)
from schoolminer.storage.sqlite_store import (
    get_crawl_job,
    update_crawl_status,
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
            search_page = parse_search_response(search_response)

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

    console.print("[green]Response validated successfully.[/green]")

    console.print(f"PageCount: {search_page.page_count:,}")

    console.print(f"Records returned: {len(search_page.records)}")

    if search_page.records:
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

        for record in search_page.records:
            if record.ownership_id == 1:
                ownership = "Private"

            elif record.ownership_id == 2:
                ownership = "Public"

            else:
                ownership = (
                    str(record.ownership_id) if record.ownership_id is not None else "Unknown"
                )

            table.add_row(
                str(record.institution_id),
                record.institution_name,
                record.region or "",
                record.town_name or "",
                record.phone_raw or "",
                ownership,
            )

        console.print(table)

        console.print()

        console.print("[bold]Validated first record[/bold]")

        first_record = search_page.records[0]

        console.print(f"Institution ID: {first_record.institution_id!r}")

        console.print(f"Institution name: {first_record.institution_name!r}")

        console.print(f"Town: {first_record.town_name!r}")

        console.print(f"Region: {first_record.region!r}")

        console.print(f"Phone raw: {first_record.phone_raw!r}")

        console.print(f"Ownership ID: {first_record.ownership_id!r}")

        console.print(f"Logo raw: {first_record.logo_raw!r}")

    else:
        console.print("[yellow]No records returned.[/yellow]")


@app.command("scrape")
def scrape(
    limit: int = typer.Option(
        10,
        "--limit",
        min=1,
        help=(
            "Minimum number of records to acquire during this run. "
            "The crawler always stops at a complete page boundary."
        ),
    ),
    resume: Optional[str] = typer.Option(
        None,
        "--resume",
        help="Resume an existing crawl by its crawl ID.",
    ),
    region: Optional[str] = typer.Option(
        None,
        "--region",
        help=("Directory region filter for a new crawl. Defaults to All."),
    ),
    delay: float = typer.Option(
        1.0,
        "--delay",
        min=0.0,
        help="Seconds to wait between completed page requests.",
    ),
    insecure: bool = typer.Option(
        False,
        "--insecure",
        help=(
            "Disable TLS certificate verification for the "
            "directory's currently misconfigured certificate."
        ),
    ),
) -> None:
    """Start or resume a raw Ghana Education Directory crawl."""

    console.rule("[bold]Ghana Education Directory Crawl[/bold]")

    if insecure:
        console.print()
        console.print(
            "[bold yellow]WARNING: TLS certificate verification is disabled.[/bold yellow]"
        )

    if resume is not None:
        if region is not None:
            console.print()
            console.print("[bold red]--region cannot be changed when resuming a crawl.[/bold red]")

            raise typer.Exit(code=2)

        crawl = get_crawl_job(
            STATE_DB_PATH,
            resume,
        )

        if crawl is None:
            console.print()
            console.print(f"[bold red]Crawl does not exist: {resume}[/bold red]")

            raise typer.Exit(code=1)

        console.print()
        console.print(f"Resuming crawl: [cyan]{crawl.crawl_id}[/cyan]")

        console.print(f"Category: {crawl.category}")

        console.print(f"Region: {crawl.region_filter}")

        console.print(f"Next page: {crawl.next_page:,}")

        console.print(f"Records already saved: {crawl.records_saved:,}")

    else:
        selected_region = region if region is not None else "All"

        crawl = create_directory_crawl(
            STATE_DB_PATH,
            region_filter=selected_region,
        )

        console.print()
        console.print(f"Created crawl: [cyan]{crawl.crawl_id}[/cyan]")

        console.print(f"Category: {crawl.category}")

        console.print(f"Region: {crawl.region_filter}")

    console.print(f"Run limit: {limit:,} records minimum")

    console.print(f"Page delay: {delay:g} seconds")

    console.print()

    def on_page_completed(
        page_number: int,
        total_pages: int,
        record_count: int,
    ) -> None:
        console.print(
            f"[green]✓[/green] Page {page_number:,}/{total_pages:,} — {record_count} records"
        )

    def on_page_retry(
        page_number: int,
        attempt: int,
        max_attempts: int,
        retry_delay: float,
        error: str,
    ) -> None:
        console.print(
            "[yellow]⚠[/yellow] "
            f"Page {page_number:,} "
            f"attempt {attempt}/{max_attempts} "
            f"failed: {error}"
        )

        console.print(f"  Retrying in {retry_delay:g} seconds...")

    try:
        with build_client(verify=not insecure) as client:
            final_crawl = run_directory_crawl(
                client,
                state_db_path=STATE_DB_PATH,
                raw_dir=RAW_DIR,
                crawl_id=crawl.crawl_id,
                limit=limit,
                delay_seconds=delay,
                on_page_completed=(on_page_completed),
                on_page_retry=on_page_retry,
            )

    except KeyboardInterrupt:
        update_crawl_status(
            STATE_DB_PATH,
            crawl.crawl_id,
            "PAUSED",
            datetime.now(timezone.utc),
        )

        paused_crawl = get_crawl_job(
            STATE_DB_PATH,
            crawl.crawl_id,
        )

        console.print()
        console.print("[yellow]Crawl interrupted and paused.[/yellow]")

        if paused_crawl is not None:
            console.print(f"Next page: {paused_crawl.next_page:,}")

        console.print()
        console.print("Resume with:")

        console.print(
            "[cyan]"
            "schoolminer scrape "
            f"--resume {crawl.crawl_id} "
            f"--limit {limit}" + (" --insecure" if insecure else "") + "[/cyan]"
        )

        raise typer.Exit(code=130)

    except Exception as exc:
        failed_crawl = get_crawl_job(
            STATE_DB_PATH,
            crawl.crawl_id,
        )

        console.print()
        console.print(f"[bold red]Crawl failed: {exc}[/bold red]")

        if failed_crawl is not None:
            console.print(f"Crawl ID: {failed_crawl.crawl_id}")

            console.print(f"Next page: {failed_crawl.next_page:,}")

            console.print()
            console.print("Retry with:")

            console.print(
                "[cyan]"
                "schoolminer scrape "
                f"--resume {failed_crawl.crawl_id} "
                f"--limit {limit}" + (" --insecure" if insecure else "") + "[/cyan]"
            )

        raise typer.Exit(code=1) from exc

    console.print()

    if final_crawl.status == "COMPLETED":
        console.print("[bold green]Crawl completed.[/bold green]")

    elif final_crawl.status == "PAUSED":
        console.print("[bold yellow]Crawl paused at the requested run limit.[/bold yellow]")

    else:
        console.print(f"Crawl status: {final_crawl.status}")

    console.print(f"Crawl ID: [cyan]{final_crawl.crawl_id}[/cyan]")

    console.print(f"Records saved: {final_crawl.records_saved:,}")

    console.print(f"Next page: {final_crawl.next_page:,}")

    if final_crawl.total_pages is not None:
        console.print(f"Total pages: {final_crawl.total_pages:,}")

    raw_crawl_dir = RAW_DIR / "crawls" / final_crawl.crawl_id

    console.print(f"Raw data: {raw_crawl_dir}")

    if final_crawl.status == "PAUSED":
        console.print()
        console.print("Resume with:")

        console.print(
            "[cyan]"
            "schoolminer scrape "
            f"--resume {final_crawl.crawl_id} "
            f"--limit {limit}" + (" --insecure" if insecure else "") + "[/cyan]"
        )


if __name__ == "__main__":
    app()
