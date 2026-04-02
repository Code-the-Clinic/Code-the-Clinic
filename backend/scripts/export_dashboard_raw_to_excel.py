"""One-off utility to export dashboard source data to Excel.

This script is not used by the web app at runtime; it is a
standalone tool that can be run from the command line when
faculty or admins need a raw dump of ClinicReport rows.

Usage examples:
    python scripts/export_dashboard_raw_to_excel.py
    python scripts/export_dashboard_raw_to_excel.py --output "exports/dashboard_raw.xlsx"
"""

import argparse
import os
from datetime import datetime
from pathlib import Path

import django
from openpyxl import Workbook


def bootstrap_django() -> None:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Export raw data powering the dashboard into Excel.'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='',
        help='Optional output path for the .xlsx file.',
    )
    return parser.parse_args()


def build_default_output_path() -> Path:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_dir = Path(__file__).resolve().parent.parent / 'exports'
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir / f'dashboard_raw_{timestamp}.xlsx'


def export_clinic_reports(output_path: Path) -> int:
    from clinic_reports.models import ClinicReport

    wb = Workbook()
    ws = wb.active
    ws.title = 'clinic_reports_raw'

    headers = [
        'id',
        'created_at_utc',
        'first_name',
        'last_name',
        'email',
        'sport',
        'semester',
        'week',
        'immediate_emergency_care',
        'musculoskeletal_exam',
        'non_musculoskeletal_exam',
        'taping_bracing',
        'rehabilitation_reconditioning',
        'modalities',
        'pharmacology',
        'injury_illness_prevention',
        'non_sport_patient',
        'interacted_hcps',
        'healthcare_provider',
        'total_experiences',
    ]
    ws.append(headers)

    qs = ClinicReport.objects.select_related('sport', 'healthcare_provider').order_by('id')
    count = 0

    for report in qs.iterator():
        total_experiences = (
            (report.immediate_emergency_care or 0)
            + (report.musculoskeletal_exam or 0)
            + (report.non_musculoskeletal_exam or 0)
            + (report.taping_bracing or 0)
            + (report.rehabilitation_reconditioning or 0)
            + (report.modalities or 0)
            + (report.pharmacology or 0)
            + (report.injury_illness_prevention or 0)
            + (report.non_sport_patient or 0)
        )

        ws.append([
            report.id,
            report.created_at.isoformat() if report.created_at else '',
            report.first_name,
            report.last_name,
            report.email,
            report.sport.name if report.sport else '',
            report.semester,
            report.week,
            report.immediate_emergency_care,
            report.musculoskeletal_exam,
            report.non_musculoskeletal_exam,
            report.taping_bracing,
            report.rehabilitation_reconditioning,
            report.modalities,
            report.pharmacology,
            report.injury_illness_prevention,
            report.non_sport_patient,
            report.interacted_hcps,
            report.healthcare_provider.name if report.healthcare_provider else '',
            total_experiences,
        ])
        count += 1

    wb.save(output_path)
    return count


def main() -> None:
    args = parse_args()
    bootstrap_django()

    output_path = Path(args.output) if args.output else build_default_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = export_clinic_reports(output_path)
    print(f'Export complete: {rows} rows written to {output_path}')


if __name__ == '__main__':
    main()
