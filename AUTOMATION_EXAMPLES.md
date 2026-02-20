# Automation Examples for Brunata Online Integration

This document contains various automation examples showing how to use the Brunata Online integration in your Home Assistant setup.

## Table of Contents

- [Consumption Monitoring](#consumption-monitoring)
- [Cost Tracking](#cost-tracking)
- [Energy Optimization](#energy-optimization)
- [Notifications](#notifications)
- [Climate Control Integration](#climate-control-integration)

## Consumption Monitoring

### Daily Consumption Alert

Get notified if your heating consumption exceeds a threshold:

```yaml
automation:
  - alias: "High heating consumption alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.brunata_consumption_heating_*
        above: 50
        for:
          hours: 1
    action:
      - service: notify.mobile_app
        data:
          title: "⚠️ High Heating Usage"
          message: "Your heating consumption is {{ states('sensor.brunata_consumption_heating_*') }} kWh today"

  - alias: "High water consumption alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.brunata_consumption_water_*
        above: 100
    action:
      - service: notify.mobile_app
        data:
          title: "💧 High Water Usage"
          message: "Water consumption has reached {{ states('sensor.brunata_consumption_water_*') }} units"
```

### Weekly Consumption Summary

Send a weekly report comparing consumption:

```yaml
automation:
  - alias: "Weekly consumption report"
    trigger:
      - platform: time
        at: "18:00:00"
      - platform: template
        value_template: "{{ now().weekday() == 6 }}"  # Sunday
    action:
      - service: notify.mobile_app
        data:
          title: "📊 Weekly Consumption Summary"
          message: |
            Heating: {{ states('sensor.brunata_consumption_heating_*') }} kWh
            Water: {{ states('sensor.brunata_consumption_water_*') }} units
            Electricity: {{ states('sensor.brunata_consumption_electricity_*') }} kWh
```

## Cost Tracking

### Calculate Monthly Heating Costs

Create a template sensor to estimate costs:

```yaml
template:
  - sensor:
      - name: "Estimated Heating Cost"
        unit_of_measurement: "DKK"
        state: >
          {% set consumption = states('sensor.brunata_consumption_heating_*') | float(0) %}
          {% set price_per_kwh = 2.5 %}
          {{ (consumption * price_per_kwh) | round(2) }}
        icon: mdi:currency-usd

      - name: "Estimated Water Cost"
        unit_of_measurement: "DKK"
        state: >
          {% set consumption = states('sensor.brunata_consumption_water_*') | float(0) %}
          {% set price_per_unit = 0.5 %}
          {{ (consumption * price_per_unit) | round(2) }}
        icon: mdi:water-outline
```

### Budget Warning

Alert when monthly costs exceed budget:

```yaml
automation:
  - alias: "Heating budget exceeded"
    trigger:
      - platform: numeric_state
        entity_id: sensor.estimated_heating_cost
        above: 1000  # DKK
    action:
      - service: notify.mobile_app
        data:
          title: "💰 Budget Alert"
          message: "Heating costs this month: {{ states('sensor.estimated_heating_cost') }} DKK"
          data:
            tag: "budget_alert"
```

## Energy Optimization

### Detect Unusual Consumption Patterns

Alert on sudden spikes in consumption:

```yaml
automation:
  - alias: "Unusual heating consumption spike"
    trigger:
      - platform: state
        entity_id: sensor.brunata_consumption_heating_*
    condition:
      - condition: template
        value_template: >
          {% set current = trigger.to_state.state | float(0) %}
          {% set previous = trigger.from_state.state | float(0) %}
          {{ (current - previous) > 20 }}
    action:
      - service: notify.mobile_app
        data:
          title: "🔥 Heating Spike Detected"
          message: "Heating increased by {{ (trigger.to_state.state | float - trigger.from_state.state | float) | round(1) }} kWh"
```

### Compare to Previous Month

Create a template to track month-over-month changes:

```yaml
template:
  - sensor:
      - name: "Heating Consumption Change"
        unit_of_measurement: "%"
        state: >
          {% set current = states('sensor.brunata_consumption_heating_*') | float(0) %}
          {% set history = state_attr('sensor.brunata_consumption_heating_*', 'raw_data') %}
          {% if history and history.consumptionLines | length > 1 %}
            {% set previous = history.consumptionLines[-2].consumptionValues[0].consumption | float(0) %}
            {% if previous > 0 %}
              {{ ((current - previous) / previous * 100) | round(1) }}
            {% else %}
              0
            {% endif %}
          {% else %}
            0
          {% endif %}
        icon: mdi:chart-line
```

## Notifications

### Morning Consumption Report

Start your day with current consumption levels:

```yaml
automation:
  - alias: "Morning consumption report"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: notify.mobile_app
        data:
          title: "🌅 Good Morning!"
          message: |
            Current consumption this month:
            🌡️ Heating: {{ states('sensor.brunata_consumption_heating_*') }} kWh
            💧 Water: {{ states('sensor.brunata_consumption_water_*') }} units
            ⚡ Electricity: {{ states('sensor.brunata_consumption_electricity_*') }} kWh
```

### Low Consumption Congratulations

Positive reinforcement for energy saving:

```yaml
automation:
  - alias: "Low consumption achievement"
    trigger:
      - platform: time
        at: "23:59:00"
    condition:
      - condition: numeric_state
        entity_id: sensor.brunata_consumption_heating_*
        below: 30
    action:
      - service: notify.mobile_app
        data:
          title: "🎉 Great Job!"
          message: "You kept heating consumption low today at {{ states('sensor.brunata_consumption_heating_*') }} kWh"
```

## Climate Control Integration

### Adjust Thermostat Based on Consumption

Automatically reduce heating when consumption is high:

```yaml
automation:
  - alias: "Reduce heating on high consumption"
    trigger:
      - platform: numeric_state
        entity_id: sensor.brunata_consumption_heating_*
        above: 75
    condition:
      - condition: state
        entity_id: climate.living_room
        state: "heat"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room
        data:
          temperature: >
            {{ state_attr('climate.living_room', 'temperature') - 1 }}
      - service: notify.mobile_app
        data:
          title: "🌡️ Thermostat Adjusted"
          message: "Reduced temperature by 1°C due to high consumption"
```

### Away Mode Energy Saving

When you're away, monitor and alert on unexpected consumption:

```yaml
automation:
  - alias: "Away mode consumption alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.brunata_consumption_heating_*
        above: 20
    condition:
      - condition: state
        entity_id: input_boolean.away_mode
        state: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "⚠️ Unexpected Consumption"
          message: "Heating consumption is {{ states('sensor.brunata_consumption_heating_*') }} kWh while you're away"
          data:
            actions:
              - action: "check_thermostats"
                title: "Check Thermostats"
```

### Weekend vs Weekday Patterns

Track different consumption patterns:

```yaml
template:
  - binary_sensor:
      - name: "Weekend Heating Pattern"
        state: >
          {{ now().weekday() >= 5 }}
        icon: mdi:calendar-weekend

automation:
  - alias: "Weekend heating adjustment"
    trigger:
      - platform: state
        entity_id: binary_sensor.weekend_heating_pattern
        to: "on"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room
        data:
          temperature: 21  # Warmer on weekends
```

## Advanced Usage

### Energy Dashboard Integration

Add Brunata sensors to your energy dashboard in `configuration.yaml`:

```yaml
# This is configured through the UI, but here's the concept
energy:
  sensors:
    - sensor: sensor.brunata_consumption_heating_*
      name: Heating
    - sensor: sensor.brunata_consumption_water_*
      name: Water
    - sensor: sensor.brunata_consumption_electricity_*
      name: Electricity
```

### Lovelace Dashboard Card

Create a comprehensive consumption dashboard:

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Brunata Meters
    entities:
      - entity: sensor.brunata_heating_meters
        name: Heating Meters
      - entity: sensor.brunata_water_meters
        name: Water Meters
      - entity: sensor.brunata_electricity_meters
        name: Electricity Meters

  - type: horizontal-stack
    cards:
      - type: gauge
        entity: sensor.brunata_consumption_heating_*
        name: Heating
        min: 0
        max: 100
        severity:
          green: 0
          yellow: 50
          red: 75
      
      - type: gauge
        entity: sensor.brunata_consumption_water_*
        name: Water
        min: 0
        max: 200
        severity:
          green: 0
          yellow: 100
          red: 150

  - type: markdown
    content: |
      **Last Update:** {{ relative_time(states.sensor.brunata_consumption_heating_*.last_updated) }}
      
      **Monthly Costs (estimated):**
      - Heating: {{ states('sensor.estimated_heating_cost') }} DKK
      - Water: {{ states('sensor.estimated_water_cost') }} DKK
```

## Troubleshooting Automations

If automations aren't triggering:

1. **Check entity IDs**: Replace `*` with actual entity IDs
2. **Verify sensors exist**: Go to Developer Tools → States
3. **Test conditions**: Use Template Editor in Developer Tools
4. **Check logs**: Look for automation errors in the logs

## Contributing

Have a cool automation idea? Submit it via GitHub issues or pull requests!
