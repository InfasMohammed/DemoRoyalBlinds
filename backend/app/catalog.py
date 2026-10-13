"""Illustrative fixtures, never represented as Royal Blinds business records."""
from datetime import datetime
from zoneinfo import ZoneInfo

FABRICS = [
    {'id': 'linen_blackout', 'name': 'Linen-look blackout', 'sku': 'DEMO-FAB-101',
     'roll_width_m': 3.2, 'stock_lm': 28.0, 'cost_per_lm': 52.0, 'lead_days': 7,
     'transmission': 'Blackout', 'color': 'Warm ivory', 'compatible': ['motorized_roller', 'manual_roller', 'curtain'],
     'source': 'Demo warehouse · WH-001'},
    {'id': 'solar_screen', 'name': 'Solar screen · 5% openness', 'sku': 'DEMO-FAB-102',
     'roll_width_m': 3.0, 'stock_lm': 90.0, 'cost_per_lm': 44.0, 'lead_days': 5,
     'transmission': 'Filtered light', 'color': 'Stone grey', 'compatible': ['motorized_roller', 'manual_roller'],
     'source': 'Demo warehouse · WH-002'},
    {'id': 'premium_blackout', 'name': 'Performance blackout', 'sku': 'DEMO-FAB-103',
     'roll_width_m': 3.2, 'stock_lm': 120.0, 'cost_per_lm': 65.0, 'lead_days': 4,
     'transmission': 'Blackout', 'color': 'Soft white', 'compatible': ['motorized_roller', 'manual_roller', 'curtain'],
     'source': 'Demo warehouse · WH-003'},
]

PRODUCTS = {
    'motorized_roller': {'name': 'Motorized roller blinds', 'hardware_aed': 85, 'motor_aed': 245,
                         'labor_hours': 0.55, 'install_hours': 0.40, 'max_width_m': 3.0, 'max_height_m': 3.5},
    'manual_roller': {'name': 'Manual roller blinds', 'hardware_aed': 65, 'motor_aed': 0,
                     'labor_hours': 0.40, 'install_hours': 0.30, 'max_width_m': 3.0, 'max_height_m': 3.5},
    'curtain': {'name': 'Curtains with manual tracks', 'hardware_aed': 95, 'motor_aed': 0,
                'labor_hours': 0.85, 'install_hours': 0.50, 'max_width_m': 4.0, 'max_height_m': 4.0},
}

# All rates and policies are interview assumptions, not actual company terms.
POLICY = {'labor_aed_hour': 45, 'installation_aed_hour': 65, 'margin_fraction': 0.30,
          'vat_fraction': 0.05, 'waste_fraction': 0.08, 'factory_hours_day': 6,
          'installation_hours_day': 6, 'queue_business_days': 2,
          'source': 'Demo estimating policy · EST-001'}


def today():
    return datetime.now(ZoneInfo('Asia/Dubai')).date()
