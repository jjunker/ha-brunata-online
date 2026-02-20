# Brunata Online Integration for Home Assistant

A custom Home Assistant integration that connects to your Brunata Online portal to monitor heating, water, and electricity consumption from your apartment building's metering system.

## Features

- 🌡️ Monitor heating consumption from radiators
- 💧 Track water usage
- ⚡ View electricity consumption
- 🔄 Automatic updates every 15 minutes
- 🔐 Secure Azure AD B2C authentication with automatic token refresh
- 📊 Proper energy device classes for Home Assistant Energy dashboard
- 🏢 Perfect for apartment buildings with Brunata metering systems

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/yourusername/ha-brunata-online`
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
- **Heating Meters**: Number of heating allocation units
- **Water Meters**: Number of water meters
- **Electricity Meters**: Number of electricity meters

### Consumption Sensors
- **Monthly Consumption**: Energy usage tracked with proper kWh units
- **Historical Data**: Access to consumption history via sensor attributes

All consumption sensors support the Home Assistant Energy dashboard and have the following:
- Device class: `energy`
- State class: `total_increasing`
- Unit: `kWh`

## Dashboard Examples

### Simple Consumption Card

```yaml
type: entities
entities:
  - entity: sensor.brunata_heating_meters
  - entity: sensor.brunata_consumption_heating_*
    name: Heating Consumption
  - entity: sensor.brunata_consumption_water_*
    name: Water Consumption
title: Brunata Consumption
```

### Energy Dashboard Integration

The consumption sensors automatically appear in the Home Assistant Energy dashboard. To add them:

1. Go to **Settings** → **Dashboards** → **Energy**
2. Click **Add Consumption**
3. Select your Brunata consumption sensors
4. Configure the energy source as needed

### Gauge Card for Current Usage

```yaml
type: gauge
entity: sensor.brunata_consumption_heating_*
name: Heating Usage
unit: kWh
min: 0
max: 1000
```

## Automations

### High Consumption Alert

```yaml
automation:
  - alias: "Alert on high heating consumption"
    trigger:
      - platform: numeric_state
        entity_id: sensor.brunata_consumption_heating_*
        above: 500
    action:
      - service: notify.mobile_app
        data:
          title: "High Heating Usage"
          message: "Heating consumption has exceeded 500 kWh this month"
```

### Daily Consumption Report

```yaml
automation:
  - alias: "Daily consumption summary"
    trigger:
      - platform: time
        at: "20:00:00"
    action:
      - service: notify.mobile_app
        data:
          title: "Today's Consumption"
          message: >
            Heating: {{ states('sensor.brunata_consumption_heating_*') }} kWh
            Water: {{ states('sensor.brunata_consumption_water_*') }} kWh
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

- Based on research from the [Home Assistant Community Forum](https://community.home-assistant.io/t/brunata-integration-api-based/595447)
- Authentication flow inspired by YukiElectronics' initial work
- Azure B2C implementation pattern from Home Assistant FordPass integration

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/yourusername/ha-brunata-online/issues).

## License

This project is licensed under the MIT License - see the LICENSE file for details.
