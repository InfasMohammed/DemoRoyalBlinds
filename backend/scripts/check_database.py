"""Read-only verification of operational, knowledge and report database access."""
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.business_data import data_source, load_operations, load_database_knowledge
from app.store import ReportStore


def main():
    if data_source() != 'supabase':
        raise SystemExit('Set BUSINESS_DATA_SOURCE=supabase and configure both backend Supabase variables securely.')
    operations = load_operations()
    corpus = load_database_knowledge()
    reports = ReportStore().list()
    print(f"PASS: Supabase returned {len(operations['fabrics'])} materials, {len(operations['products'])} manufacturing profiles, "
          f"{len(corpus['products'])} portfolio products, {len(corpus['chunks'])} knowledge passages and {len(reports)} recent reports.")
    print('Sample values: ' + str(operations['is_sample']) + '. No data was changed.')


if __name__ == '__main__':
    main()
