# Feature Plan: Per-Profile TTS Entities

## Overview
Create individual TTS entities for each voice profile, allowing users to see and use profiles as separate entities in Home Assistant (e.g., `tts.xai_custom_tts_morning_news`, `tts.xai_custom_tts_bedtime_story`).

## Goals
- Each voice profile becomes a discoverable, selectable TTS entity
- Users can target specific profiles directly in automations
- Profiles appear in the UI with their settings visible
- Dynamic entity creation/deletion when profiles change

---

## Architecture

### Entity Structure

```
tts.xai_custom_tts              # Main entity (default/current behavior)
tts.xai_custom_tts_profile_1    # Profile-specific entity
tts.xai_custom_tts_profile_2    # Profile-specific entity
```

### Platform Setup

**New file: `sensor.py` (or extend `tts.py`)**
- Create `XAIProfileTTSEntity` class extending `TextToSpeechEntity`
- Each instance represents one voice profile
- Stores profile name, voice settings as entity attributes

**Modified: `__init__.py`**
- Set up entity coordinator to watch for config entry options changes
- When profiles change, trigger entity registry updates

**Modified: `config_flow.py`**
- After profile CRUD operations, signal entity coordinator to refresh

---

## Implementation Plan

### Phase 1: Entity Foundation

#### 1.1 Create Profile TTS Entity Class
```python
# custom_components/xai_custom_tts/tts.py (additions)

class XAIProfileTTSEntity(TextToSpeechEntity):
    """TTS entity for a specific voice profile."""
    
    def __init__(self, hass, api_key, config_entry, profile_name, profile_data):
        self.hass = hass
        self._api_key = api_key
        self._config_entry = config_entry
        self._profile_name = profile_name
        self._profile_data = profile_data
        self._name = f"xAI Custom TTS {profile_name}"
        self._unique_id = f"{DOMAIN}_tts_{profile_name.lower().replace(' ', '_')}"
    
    @property
    def name(self) -> str:
        return f"xai_custom_tts_{self._profile_name.lower().replace(' ', '_')}"
    
    @property
    def unique_id(self) -> str:
        return self._unique_id
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose profile settings as attributes."""
        return {
            "profile_name": self._profile_name,
            "voice": self._profile_data.get("voice"),
            "language": self._profile_data.get("language"),
            "codec": self._profile_data.get("codec"),
            "sample_rate": self._profile_data.get("sample_rate"),
            "bit_rate": self._profile_data.get("bit_rate"),
        }
    
    async def async_get_tts_audio(self, message, language, options=None):
        """Use profile settings, ignore passed options."""
        # Always use profile settings
        merged_options = {
            "voice": self._profile_data.get("voice", DEFAULT_VOICE),
            "language": self._profile_data.get("language", DEFAULT_LANGUAGE),
            "codec": self._profile_data.get("codec", DEFAULT_CODEC),
            "sample_rate": self._profile_data.get("sample_rate", DEFAULT_SAMPLE_RATE),
            "bit_rate": self._profile_data.get("bit_rate", DEFAULT_BIT_RATE),
        }
        # Call the same TTS logic as main entity
        return await self._perform_tts(message, merged_options)
```

#### 1.2 Dynamic Entity Management
```python
# custom_components/xai_custom_tts/__init__.py (additions)

async def async_setup_entry(hass, entry):
    # ... existing setup ...
    
    # Set up profile entity coordinator
    coordinator = ProfileEntityCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator
    
    # Forward to TTS platform for main entity
    await hass.config_entries.async_forward_entry_setups(entry, ["tts"])
    
    # Forward to new platform for profile entities
    await hass.config_entries.async_forward_entry_setups(entry, ["tts_profile"])
    # OR handle in same tts platform with entity discovery

class ProfileEntityCoordinator:
    """Manages creation/update/deletion of profile entities."""
    
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self._unsub_options_listener = None
    
    async def async_setup(self):
        """Listen for options changes."""
        self._unsub_options_listener = self.entry.add_update_listener(
            self._on_options_updated
        )
    
    async def _on_options_updated(hass, entry):
        """When profiles change, signal entity platform to refresh."""
        async_dispatcher_send(
            hass, 
            f"{DOMAIN}_{entry.entry_id}_profiles_updated"
        )
```

### Phase 2: Platform Integration

#### 2.1 Extend TTS Platform for Multiple Entities
```python
# custom_components/xai_custom_tts/tts.py (modifications)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up both main and profile TTS entities."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    api_key = entry_data["api_key"]
    
    entities = []
    
    # Main entity (existing behavior)
    entities.append(XAITTSProvider(hass, api_key, config_entry))
    
    # Profile entities
    voice_profiles = config_entry.options.get("voice_profiles", {})
    for profile_name, profile_data in voice_profiles.items():
        entities.append(
            XAIProfileTTSEntity(hass, api_key, config_entry, profile_name, profile_data)
        )
    
    async_add_entities(entities)
    
    # Listen for profile changes to add/remove entities
    async def on_profiles_updated():
        """Handle profile changes."""
        current_profiles = config_entry.options.get("voice_profiles", {})
        
        # Get current profile entities
        current_entities = {
            entity.unique_id: entity 
            for entity in entities 
            if isinstance(entity, XAIProfileTTSEntity)
        }
        
        # Add new profile entities
        new_entities = []
        for profile_name, profile_data in current_profiles.items():
            unique_id = f"{DOMAIN}_tts_{profile_name.lower().replace(' ', '_')}"
            if unique_id not in current_entities:
                new_entities.append(
                    XAIProfileTTSEntity(hass, api_key, config_entry, profile_name, profile_data)
                )
        
        if new_entities:
            async_add_entities(new_entities)
            entities.extend(new_entities)
    
    async_dispatcher_connect(
        hass, 
        f"{DOMAIN}_{config_entry.entry_id}_profiles_updated",
        on_profiles_updated
    )
```

### Phase 3: Entity Cleanup

#### 3.1 Handle Profile Deletion
When a profile is deleted, the entity should be removed from the registry:

```python
# In config_flow.py when deleting profile

async def async_step_delete_profile(self, user_input):
    # ... existing delete logic ...
    
    # Also remove entity from registry
    entity_registry = async_get_entity_registry(self.hass)
    profile_name = user_input["profile_name"]
    unique_id = f"{DOMAIN}_tts_{profile_name.lower().replace(' ', '_')}"
    
    entity_entry = entity_registry.async_get_entity_id(
        "tts", DOMAIN, unique_id
    )
    if entity_entry:
        entity_registry.async_remove(entity_entry)
```

### Phase 4: UI Enhancements

#### 4.1 Entity Display Names
```python
@property
def device_info(self) -> DeviceInfo:
    """Group all profile entities under main integration."""
    return DeviceInfo(
        identifiers={(DOMAIN, self._config_entry.entry_id)},
        name="xAI Custom TTS",
        manufacturer="xAI",
        model="TTS",
    )
```

#### 4.2 Entity State
- Show as "ready" when integration is loaded
- Show profile settings in entity attributes (visible in Developer Tools)

---

## Usage Examples

### Automation targeting specific profile entity
```yaml
automation:
  - alias: "Morning News"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: tts.speak
        data:
          entity_id: tts.xai_custom_tts_morning_news  # Direct profile entity
          message: "Good morning! Here's the news..."
          media_player_entity_id: media_player.bedroom_speaker
```

### See all profile entities in UI
- Go to Settings → Devices & Services → Entities
- Search "xAI" to see:
  - `tts.xai_custom_tts` (main)
  - `tts.xai_custom_tts_morning_news`
  - `tts.xai_custom_tts_bedtime_story`
  - etc.

---

## Technical Considerations

### 1. Entity ID Conflicts
- Sanitize profile names for entity IDs (spaces → underscores, lowercase)
- Handle special characters in profile names
- Prevent duplicate entity IDs if profiles have similar names

### 2. Migration Path
- Existing users with profiles get new entities automatically
- Main entity continues to work as before (backward compatible)

### 3. Performance
- Profile entities are lightweight (just store settings)
- Only make API calls when TTS is actually requested
- No polling needed

### 4. Edge Cases
- What if profile name changes? → Entity ID should stay stable (use profile name as unique_id, update friendly name)
- What if profile is deleted while TTS is in progress? → Handle gracefully

---

## Implementation Order

1. **Create `XAIProfileTTSEntity` class** in `tts.py`
2. **Modify `async_setup_entry`** to create profile entities
3. **Add dispatcher signal** for profile updates
4. **Handle entity cleanup** on profile deletion
5. **Add `device_info`** for nice UI grouping
6. **Test** entity creation, update, deletion flows
7. **Update documentation** with new entity usage examples

---

## Alternative Approaches

### Option A: Separate Platform (Recommended)
- Keep main TTS entity in `tts.py`
- Create `tts_profile.py` platform for profile entities
- Cleaner separation of concerns

### Option B: Single Platform with Discovery
- All entities in `tts.py`
- Use `async_add_entities` callback for dynamic addition
- Simpler but more complex file

### Option C: Switch Entities Instead of TTS
- Create `switch.xai_profile_morning_news` for each profile
- Switch turns profile on/off (enable/disable)
- Less useful than direct TTS entities

**Recommendation: Option A** - Clean, follows HA patterns, easy to maintain.

---

## Estimated Effort
- **Phase 1**: 2-3 hours (entity class, coordinator)
- **Phase 2**: 2-3 hours (platform integration, dynamic updates)
- **Phase 3**: 1-2 hours (cleanup, edge cases)
- **Phase 4**: 1 hour (UI polish, testing)
- **Total**: ~6-9 hours of development
