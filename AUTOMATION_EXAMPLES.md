# Automation Examples for Brunata Online Integration

This document contains various automation examples showing how to use the Brunata Online integration in your Home Assistant setup.

**Note**: Replace room names like `kitchen`, `living_room`, `bedroom`, `room_1` with your actual room names from your Brunata setup. Sensor names are derived from the placement field in your Brunata account.

## Table of Contents

- [Room-Specific Monitoring](#room-specific-monitoring)
- [Total Consumption Monitoring](#total-consumption-monitoring)
- [Cost Tracking](#cost-tracking)
- [Energy Optimization](#energy-optimization)
- [Notifications](#notifications)
- [Climate Control Integration](#climate-control-integration)

## Room-Specific Monitoring

### Individual Room High Consumption Alert

Get notified if a specific room's heating exceeds a threshold:

```yaml
automation:
  - alias: "High kitchen heating alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.brunata_kitchen
        above: 50
        for:
          hours: 2
    action:
      - service: notify.mobile_app
        data:
          title: "⚠️ High Kitchen Heating"
          message: "Kitchen radiator consumption is {{ states('sensor.brunata_kitchen') }} units"

  - alias: "Bedroom heating spike"
    trigger:
      - platform: numeric_state
        entity_id: sensor.brunata_bedroom
        above: 30
    action:
      - service: notify.mobile_app
        data:
          title: "🛏️ Bedroom Heating Spike"
          message: "Bedroom heating is unusually high: {{ states('sensor.brunata_bedroom') }} units"
```

### All Rooms Comparison

Monitor when one room uses significantly more than others:

```yaml
automation:
  - alias: "Unbalanced heating usage"
    trigger:
      - platform: time_pattern
        hours: "/6"
    condition:
      - condition: template
        value_template: >
          {% set kitchen = states('sensor.brunata_kitchen') | float %}
          {% set living = states('sensor.brunata_living_room') | float %}
          {% set bedroom = states('sensor.brunata_bedroom') | float %}
          {{ (kitchen > living * 2) or (kitchen > bedroom * 2) }}
    action:
      - service: notify.mobile_app
        data:
          title: "⚖️ Unbalanced Heating"
          message: >
            Kitchen: {{ states('sensor.brunata_kitchen') }} units
            Living: {{ states('sensor.brunata_living_room') }} units
            Bedroom: {{ states('sensor.brunata_bedroom') }} units
```

## Total Consumption Monitoring

### Weekly Consumption Summary

Send a weekly report with all room breakdowns:

```yaml
automation:
  - alias: "Weekly heating report"
    trigger:
      - platform: time
        at: "18:00:00"
    condition:
      - condition: time
        weekday:
          - sun
    action:
      - service: notify.mobile_app
        data:
          title: "📊 Weekly Heating Summary"
          message: |
            Kitchen: {{ states('sensor.brunata_kitchen') }} units
            Living Room: {{ states('sensor.brunata_living_room') }} units  
            Bedroom: {{ states('sensor.brunata_bedroom') }} units
            Room 1: {{ states('sensor.brunata_room_1') }} units
            Room 2: {{ states('sensor.brunata_room_2') }} units
            Total Meters: {{ states('sensor.brunata_heating_meters') }}
```

### Daily Consumption Change Detection

Alert when today's consumption differs significantly from yesterday:

```yaml
automation:
  - alias: "Heating consumption spike detected"
    trigger:
      - platform: state
        entity_id: sensor.brunata_kitchen
    condition:
      - condition: template
        value_template: >
          {% set old = trigger.from_state.state | float(0) %}
          {% set new = trigger.to_state.state | float(0) %}
          {{ (new > old * 1.5) and (new - old > 10) }}
    action:
      - service: notify.mobile_app
        data:
          title: "📈 Consumption Spike"
          message: >
            Kitchen heating jumped from {{ trigger.from_state.state }} to {{ trigger.to_state.state }} units
```

## Cost Tracking

### Calculate Total Heating Costs

Create template sensors to estimate costs for all rooms:

```yaml
template:
  - sensor:
      - name: "Total Heating Cost"
        unit_of_measurement: "DKK"
        state: >
          {% set kitchen = states('sensor.brunata_kitchen') | float(0) %}
          {% set living = states('sensor.brunata_living_room') | float(0) %}
          {% set bedroom = states('sensor.brunata_bedroom') | float(0) %}
          {% set room1 = states('sensor.brunata_room_1') | float(0) %}
          {% set room2 = states('sensor.brunata_room_2') | float(0) %}
          {% set total = kitchen + living + bedroom + room1 + room2 %}
          {% set price_per_unit = 2.5 %}
          {{ (total * price_per_unit) | round(2) }}
        icon: mdi:currency-usd

      - name: "Kitchen Heating Cost"
        unit_of_measurement: "DKK"
        state: >
          {% set consumption = states('sensor.brunata_kitchen') | float(0) %}
          {% set price_per_unit = 2.5 %}
          {{ (consumption * price_per_unit) | round(2) }}
        icon: mdi:radiator

      - name: "Living Room Heating Cost"
        unit_of_measurement: "DKK"
        state: >
          {% set consumption = states('sensor.brunata_living_room') | float(0) %}
          {% set price_per_unit = 2.5 %}
          {{ (consumption * price_per_unit) | round(2) }}
        icon: mdi:sofa
```

### Budget Warning

Alert when monthly costs exceed budget:

```yaml
automation:
  - alias: "Heating budget exceeded"
    trigger:
      - platform: numeric_state
        entity_id: sensor.total_heating_cost
        above: 1000  # DKK
    action:
      - service: notify.mobile_app
        data:
          title: "💰 Budget Alert"
          message: "Total heating costs: {{ states('sensor.total_heating_cost') }} DKK"
          data:
            tag: "budget_alert"
            
  - alias: "Individual room cost alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.kitchen_heating_cost
        above: 200
    action:
      - service: notify.mobile_app
        data:
          title: "💰 Kitchen Heating Cost High"
          message: "Kitchen heating alone is {{ states('sensor.kitchen_heating_cost') }} DKK this month"
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
