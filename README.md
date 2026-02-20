# Brunata Online Integration for Home Assistant

A custom Home Assistant integration that connects to your Brunata Online portal to monitor heating, water, and electricity consumption from your apartment building's metering system.

## Features

- 🌡️ Monitor heating consumption from radiators
- 💧 Track water usage
- ⚡ View electricity consumption
- 🔄 Automatic updates every 15 minutes
- 🔐 Secure Azure AD B2C authentication with automatic token refresh
- 📊 Heating allocation unit tracking for cost distribution
- 🏢 Perfect for apartment buildings with Brunata metering systems

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/jjunker/ha-brunata-online`
6. Category: Integration
7. Click "Add"
8. Search for "Brunata Online"
9. Click "Download"
10. Restart Home Assistant

### Manual Installation

1. Download the latest release from GitHub
2. Create a `brunata_online` folder in your `custom_components` directory
3. Copy all files from `custom_components/brunata_online` into the folder
4. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Brunata Online"
4. Enter your Brunata Online credentials:
   - **Username**: Your email address for online.brunata.com
   - **Password**: Your Brunata Online password

The integration will authenticate using Azure AD B2C and securely store refresh tokens for automatic reauthentication.

## Usage

Once configured, the integration creates sensors for:

### Meter Count Sensors
- **sensor.brunata_heating_meters**: Number of heating allocation units
- **sensor.brunata_water_meters**: Number of water meters
- **sensor.brunata_electricity_meters**: Number of electricity meters

### Individual Radiator Sensors

Each radiator/meter in your apartment gets its own sensor based on the placement name from Brunata:
- **sensor.brunata_kitchen**
- **sensor.brunata_living_room**
- **sensor.brunata_bedroom**
- **sensor.brunata_room_1**
- **sensor.brunata_room_2**
- etc.

**Note**: Sensor names are derived from the placement field in your Brunata account. Names may vary (e.g., "Køkken", "Kitchen", "Stue", "Living room").

Each radiator sensor provides:
- **Total consumption in heating allocation units** (automatically scaled using meter-specific factors)
- **Attributes**: meter_id, meter_number, placement, scale, latest_consumption, latest_date
- **Daily consumption data** from the past 30 days

**About Heating Allocation Units**: Brunata uses a proportional allocation system where radiators measure relative heating usage, not direct energy consumption. Each room's usage is scaled by factors like radiator size and location. These units are used to fairly distribute heating costs among residents.

All consumption sensors have:
- State class: `total_increasing`
- Unit: `units`
- Icon: `mdi:radiator`

**Note**: These sensors track heating allocation units, not direct kWh energy consumption, so they won't work with the Home Assistant Energy dashboard. Use them for cost tracking and consumption monitoring instead.

## Dashboard Examples

### Simple Consumption Card

```yaml
type: entities
entities:
  - entity: sensor.brunata_heating_meters
    name: Total Heating Meters
  - entity: sensor.brunata_kitchen
    name: Kitchen
  - entity: sensor.brunata_living_room
    name: Living Room
  - entity: sensor.brunata_bedroom
    name: Bedroom
title: Brunata Radiators
```

### All Radiators Overview

```yaml
type: entities
title: Heating by Room
entities:
  - type: custom:auto-entities
    filter:
      include:
        - entity_id: sensor.brunata_*
          not:
            entity_id: "*_meters"
    sort:
      method: state
      reverse: true
```

### Gauge Card for Current Usage

```yaml
type: gauge
entity: sensor.brunata_kitchen
name: Kitchen Radiator
unit: units
min: 0
max: 100
```

### Bar Chart Card for All Rooms

```yaml
type: custom:bar-card
entities:
  - entity: sensor.brunata_kitchen
    name: Kitchen
  - entity: sensor.brunata_living_room
    name: Living Room
  - entity: sensor.brunata_bedroom
    name: Bedroom
  - entity: sensor.brunata_room_1
    name: Room 1
  - entity: sensor.brunata_room_2
    name: Room 2
title: Heating Distribution
unit_of_measurement: units
```

## Understanding Heating Costs

Brunata's heating allocation units represent your **proportional share** of the building's total heating cost. These aren't direct kWh measurements - they're weighted units that factor in radiator size, location, and usage patterns.

### How Costs Are Calculated

1. **Your total units** = Sum of all your radiator sensors
2. **Building total units** = All units in the building (from your housing association)
3. **Your heating cost** = (Your units ÷ Building total units) × Total monthly heating bill

**Example**: If you used 150 units, the building total is 10,000 units, and the monthly heating bill is 50,000 DKK:
- Your share: (150 ÷ 10,000) × 50,000 = 750 DKK

### Cost Tracking Template

Create a template sensor to estimate monthly costs:

```yaml
template:
  - sensor:
      - name: "Total Heating Units"
        unit_of_measurement: "units"
        state: >
          {% set kitchen = states('sensor.brunata_kitchen') | float(0) %}
          {% set living = states('sensor.brunata_living_room') | float(0) %}
          {% set bedroom = states('sensor.brunata_bedroom') | float(0) %}
          {{ (kitchen + living + bedroom) | round(2) }}
        icon: mdi:radiator

      - name: "Estimated Heating Cost"
        unit_of_measurement: "DKK"
        state: >
          {% set my_units = states('sensor.total_heating_units') | float(0) %}
          {% set building_units = 10000 %}  # Get from landlord
          {% set monthly_bill = 50000 %}     # Get from landlord
          {{ ((my_units / building_units) * monthly_bill) | round(2) }}
        icon: mdi:currency-usd
```

## Automations

### High Consumption Alert for Specific Room

```yaml
automation:
  - alias: "Alert on high kitchen heating"
    trigger:
      - platform: numeric_state
        entity_id: sensor.brunata_kitchen
        above: 50
    action:
      - service: notify.mobile_app
        data:
          title: "High Kitchen Heating"
          message: "Kitchen radiator consumption is unusually high: {{ states('sensor.brunata_kitchen') }} units"
```

### Total Heating Consumption Report

```yaml
automation:
  - alias: "Weekly heating summary"
    trigger:
      - platform: time
        at: "20:00:00"
    condition:
      - condition: time
        weekday:
          - sun
    action:
      - service: notify.mobile_app
        data:
          title: "Weekly Heating Report"
          message: >
            Kitchen: {{ states('sensor.brunata_kitchen') }} units
            Living Room: {{ states('sensor.brunata_living_room') }} units
            Bedroom: {{ states('sensor.brunata_bedroom') }} units
            Total: {{ states('sensor.brunata_heating_meters') }} meters
```

### Detect Radiator Not Transmitting

```yaml
automation:
  - alias: "Radiator transmission alert"
    trigger:
      - platform: state
        entity_id:
          - sensor.brunata_køkken
          - sensor.brunata_stue
          - sensor.brunata_soveværelse
    condition:
      - condition: template
        value_template: "{{ state_attr(trigger.entity_id, 'transmitting') == false }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Radiator Issue"
          message: "Radiator in {{ state_attr(trigger.entity_id, 'placement') }} is not transmitting data"
```

## Troubleshooting

### Authentication Issues

If you see authentication errors:
1. Verify your credentials are correct on online.brunata.com
2. Check the Home Assistant logs for detailed error messages
3. Try removing and re-adding the integration

### No Data Showing

- Wait 15 minutes for the first update after setup
- Check that you have active meters on your Brunata Online account
- Look for errors in **Settings** → **System** → **Logs**

### Token Expired

The integration automatically refreshes authentication tokens. If you see token errors:
1. The integration will attempt to re-authenticate automatically
2. If it fails, you may need to reconfigure with your credentials

## API Information

This integration uses the Brunata Online REST API:
- Base URL: `https://online.brunata.com/online-webservice/v1/rest/consumer`
- Authentication: Azure AD B2C OAuth 2.0 with PKCE
- Update interval: 15 minutes

## Credits

This integration was built with inspiration and patterns from several sources:

- **Initial Research**: [Home Assistant Community Forum thread](https://community.home-assistant.io/t/brunata-integration-api-based/595447) by YukiElectronics and community contributors
- **Azure B2C Authentication Pattern**: [FordPass Integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/fordpass) - Using synchronous `requests` library for B2C compatibility
- **Integration Structure**: [VW CarNet](https://github.com/home-assistant/core/tree/dev/homeassistant/components/volkswagen_we_connect) and [Kia/Hyundai](https://github.com/Hyundai-Kia-Connect/kia_uvo) integrations for OAuth flow patterns
- **Config Flow Patterns**: Home Assistant core integrations using OAuth 2.0 with PKCE

### Technical Notes

Azure AD B2C's aggressive anti-automation protection required special handling:
- CSRF tokens and transaction IDs expire in seconds
- Synchronous `requests.Session` maintains cookies better than `aiohttp` for rapid sequential requests
- Token refresh is handled via Home Assistant's executor pattern for sync code in async context

### Contributors

- Jeppe Junker - Initial implementation
- YukiElectronics - API discovery and community research
- Home Assistant Community - Testing and feedback

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/jjunker/ha-brunata-online/issues).

## License

This project is licensed under the MIT License - see the LICENSE file for details.
