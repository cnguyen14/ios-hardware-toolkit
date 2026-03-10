# iPhone DeviceEnclosureColor Mapping

## Overview

The `DeviceEnclosureColor` value is returned by Apple's lockdown service (via `ideviceinfo`,
`pymobiledevice3`, or the private `MGCopyAnswer` API). It represents the physical back/enclosure
color of the device as a numeric string.

**Important notes:**
- The same numeric ID does NOT mean the same color across different models.
- iPhone 6/6s/SE (1st gen) era devices returned **hex color codes** (e.g. `#e1e4e3`) instead of
  numeric IDs. The numeric system was introduced with iPhone 7.
- The `DeviceColor` field represents the **front glass** color (1 = Black, 2 = White). Starting
  with iPhone X (all-screen design), all models report DeviceColor = 1.
- Later-added colors (e.g. Purple for iPhone 12, Green for iPhone 13) were assigned higher IDs
  (12, 17, 18) rather than filling gaps in the original sequence.
- Some high-numbered IDs (17, 18) appear to be aliases that resolve to the same image as earlier
  IDs. These are noted below where detected.

## Data Sources

This mapping was compiled from:
1. **libimobiledevice GitHub Issue #818** - User-contributed mappings for iPhone 7 through XR
2. **iCloud Find My device image CDN** - Systematic probing of
   `statici.icloud.com/fmipmobile/deviceImages-9.0/iPhone/{model}-{front}-{enclosure}-0/`
   to discover valid enclosure color IDs, with visual verification of downloaded images
3. **Cross-referencing** with Apple's official color options per model

## ProductType to Model Name Mapping

| ProductType    | Marketing Name       | Notes                    |
|----------------|----------------------|--------------------------|
| iPhone7,2      | iPhone 6             | Hex-based colors         |
| iPhone7,1      | iPhone 6 Plus        | Hex-based colors         |
| iPhone8,1      | iPhone 6s            | Hex-based colors         |
| iPhone8,2      | iPhone 6s Plus       | Hex-based colors         |
| iPhone8,4      | iPhone SE (1st gen)  | Hex-based colors         |
| iPhone9,1      | iPhone 7             | GSM                      |
| iPhone9,3      | iPhone 7             | Global                   |
| iPhone9,2      | iPhone 7 Plus        | GSM                      |
| iPhone9,4      | iPhone 7 Plus        | Global                   |
| iPhone10,1     | iPhone 8             | GSM                      |
| iPhone10,4     | iPhone 8             | Global                   |
| iPhone10,2     | iPhone 8 Plus        | GSM                      |
| iPhone10,5     | iPhone 8 Plus        | Global                   |
| iPhone10,3     | iPhone X             | GSM                      |
| iPhone10,6     | iPhone X             | Global                   |
| iPhone11,2     | iPhone XS            |                          |
| iPhone11,4     | iPhone XS Max        | China                    |
| iPhone11,6     | iPhone XS Max        | Global                   |
| iPhone11,8     | iPhone XR            |                          |
| iPhone12,1     | iPhone 11            |                          |
| iPhone12,3     | iPhone 11 Pro        |                          |
| iPhone12,5     | iPhone 11 Pro Max    |                          |
| iPhone12,8     | iPhone SE (2nd gen)  |                          |
| iPhone13,1     | iPhone 12 mini       |                          |
| iPhone13,2     | iPhone 12            |                          |
| iPhone13,3     | iPhone 12 Pro        |                          |
| iPhone13,4     | iPhone 12 Pro Max    |                          |
| iPhone14,4     | iPhone 13 mini       |                          |
| iPhone14,5     | iPhone 13            |                          |
| iPhone14,2     | iPhone 13 Pro        |                          |
| iPhone14,3     | iPhone 13 Pro Max    |                          |
| iPhone14,6     | iPhone SE (3rd gen)  |                          |
| iPhone14,7     | iPhone 14            |                          |
| iPhone14,8     | iPhone 14 Plus       |                          |
| iPhone15,2     | iPhone 14 Pro        |                          |
| iPhone15,3     | iPhone 14 Pro Max    |                          |
| iPhone15,4     | iPhone 15            |                          |
| iPhone15,5     | iPhone 15 Plus       |                          |
| iPhone16,1     | iPhone 15 Pro        |                          |
| iPhone16,2     | iPhone 15 Pro Max    |                          |
| iPhone17,1     | iPhone 16            |                          |
| iPhone17,2     | iPhone 16 Plus       |                          |
| iPhone17,3     | iPhone 16 Pro        |                          |
| iPhone17,4     | iPhone 16 Pro Max    |                          |
| iPhone18,1     | iPhone 17 Pro        |                          |
| iPhone18,2     | iPhone 17 Pro Max    |                          |
| iPhone18,3     | iPhone 17            |                          |
| iPhone18,4     | iPhone Air           |                          |

---

## DeviceEnclosureColor Mappings by Model

### iPhone 6 / 6 Plus (iPhone7,2 / iPhone7,1) -- HEX-BASED

These models return hex color strings, not numeric IDs.

| DeviceEnclosureColor | Color Name  |
|----------------------|-------------|
| `#3b3b3c`            | Space Gray  |
| `#e1e4e3` or `#e4e7e8` | Silver   |
| `#d4c5b3` or `#e2c8b0` | Gold     |

### iPhone 6s / 6s Plus (iPhone8,1 / iPhone8,2) -- HEX-BASED

| DeviceEnclosureColor | Color Name  |
|----------------------|-------------|
| `#3b3b3c`            | Space Gray  |
| `#e4e7e8`            | Silver      |
| `#e2c8b0`            | Gold        |
| `#ecc5c1`            | Rose Gold   |

### iPhone SE 1st gen (iPhone8,4) -- HEX-BASED

| DeviceEnclosureColor | Color Name  |
|----------------------|-------------|
| `#3b3b3c`            | Space Gray  |
| `#e4e7e8`            | Silver      |
| `#e2c8b0`            | Gold        |
| `#ecc5c1`            | Rose Gold   |

---

### iPhone 7 / 7 Plus (iPhone9,1 / iPhone9,3 / iPhone9,2 / iPhone9,4)

Source: libimobiledevice issue #818, confirmed via CDN probing.

| DeviceEnclosureColor | DeviceColor | Color Name     |
|----------------------|-------------|----------------|
| 1                    | 1           | Black          |
| 2                    | 2           | Silver         |
| 3                    | 2           | Gold           |
| 4                    | 2           | Rose Gold      |
| 5                    | 1           | Jet Black      |
| 6                    | 2           | (PRODUCT)RED   |

### iPhone 8 / 8 Plus (iPhone10,1 / iPhone10,4 / iPhone10,2 / iPhone10,5)

Source: libimobiledevice issue #818, confirmed via CDN probing.

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Space Gray     |
| 2                    | Silver         |
| 3                    | Gold           |
| 6                    | (PRODUCT)RED   |

Note: All iPhone 8 models have a glass back with black front bezel for Space Gray and
white-tinted front for Silver and Gold. DeviceColor is 1 for Space Gray, 2 for Silver/Gold.

### iPhone X (iPhone10,3 / iPhone10,6)

| DeviceEnclosureColor | Color Name  |
|----------------------|-------------|
| 1                    | Space Gray  |
| 2                    | Silver      |

### iPhone XS / XS Max (iPhone11,2 / iPhone11,4 / iPhone11,6)

Source: libimobiledevice issue #818, confirmed via CDN probing.

| DeviceEnclosureColor | Color Name  |
|----------------------|-------------|
| 1                    | Space Gray  |
| 2                    | Silver      |
| 4                    | Gold        |

### iPhone XR (iPhone11,8)

Source: libimobiledevice issue #818, confirmed via CDN probing and visual inspection.

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Black          |
| 2                    | White          |
| 6                    | (PRODUCT)RED   |
| 7                    | Yellow         |
| 8                    | Coral          |
| 9                    | Blue           |

### iPhone 11 (iPhone12,1)

Confirmed via CDN probing and visual inspection.

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Black          |
| 2                    | White          |
| 6                    | (PRODUCT)RED   |
| 7                    | Yellow         |
| 11                   | Purple         |
| 12                   | Green          |

Note: IDs 17 and 18 also return valid images but appear to be aliases (same file size as
11 and 12 respectively).

### iPhone 11 Pro / 11 Pro Max (iPhone12,3 / iPhone12,5)

Confirmed via CDN probing and visual inspection.

| DeviceEnclosureColor | Color Name       |
|----------------------|------------------|
| 1                    | Space Gray       |
| 2                    | Silver           |
| 4                    | Gold             |
| 12                   | Midnight Green   |

Note: ID 18 also returns a valid image but appears to be an alias for 12 (same file size).

### iPhone SE 2nd gen (iPhone12,8)

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Black          |
| 2                    | White          |
| 6                    | (PRODUCT)RED   |

### iPhone 12 mini (iPhone13,1)

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Black          |
| 2                    | White          |
| 6                    | (PRODUCT)RED   |
| 9                    | Blue           |
| 12                   | Green          |
| 17                   | Purple         |

Note: Purple (17) was added in April 2021, several months after launch.

### iPhone 12 (iPhone13,2)

Confirmed via CDN probing and visual inspection.

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Black          |
| 2                    | White          |
| 6                    | (PRODUCT)RED   |
| 9                    | Blue           |
| 12                   | Green          |

Note: Purple (likely 17) was also added to iPhone 12, but only confirmed on 12 mini CDN.

### iPhone 12 Pro / 12 Pro Max (iPhone13,3 / iPhone13,4)

Confirmed via CDN probing and visual inspection.

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Graphite       |
| 2                    | Silver         |
| 3                    | Gold           |
| 9                    | Pacific Blue   |

### iPhone 13 mini (iPhone14,4)

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Midnight       |
| 2                    | Starlight      |
| 4                    | Pink           |
| 6                    | (PRODUCT)RED   |
| 9                    | Blue           |
| 18                   | Green          |

Note: Green (18) was added in March 2022.

### iPhone 13 (iPhone14,5)

Confirmed via CDN probing and visual inspection.

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Midnight       |
| 2                    | Starlight      |
| 4                    | Pink           |
| 6                    | (PRODUCT)RED   |
| 9                    | Blue           |
| 18                   | Green          |

Note: Green (18) was added in March 2022.

### iPhone 13 Pro / 13 Pro Max (iPhone14,2 / iPhone14,3)

Confirmed via CDN probing and visual inspection.

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Graphite       |
| 2                    | Silver         |
| 3                    | Gold           |
| 9                    | Sierra Blue    |
| 18                   | Alpine Green   |

Note: Alpine Green (18) was added in March 2022.

### iPhone SE 3rd gen (iPhone14,6)

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Midnight       |
| 2                    | Starlight      |
| 6                    | (PRODUCT)RED   |

### iPhone 14 / 14 Plus (iPhone14,7 / iPhone14,8)

Confirmed via CDN probing and visual inspection of large (infobox) images.

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Midnight       |
| 2                    | Starlight      |
| 6                    | (PRODUCT)RED   |
| 7                    | Yellow         |
| 9                    | Blue           |
| 17                   | Purple         |

Note: Yellow (7) was added in March 2023. Purple (17) and Blue (9) were launch colors.

### iPhone 14 Pro / 14 Pro Max (iPhone15,2 / iPhone15,3)

Confirmed via CDN probing and visual inspection.

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Space Black    |
| 2                    | Silver         |
| 3                    | Gold           |
| 17                   | Deep Purple    |

### iPhone 15 / 15 Plus (iPhone15,4 / iPhone15,5)

Confirmed via CDN probing and visual inspection.

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Black          |
| 4                    | Pink           |
| 7                    | Yellow         |
| 9                    | Blue           |
| 18                   | Green          |

### iPhone 15 Pro / 15 Pro Max (iPhone16,1 / iPhone16,2)

Confirmed via CDN probing and visual inspection.

| DeviceEnclosureColor | Color Name         |
|----------------------|--------------------|
| 1                    | Black Titanium     |
| 2                    | White Titanium     |
| 5                    | Natural Titanium   |
| 9                    | Blue Titanium      |

### iPhone 16 / 16 Plus (iPhone17,1 / iPhone17,2)

Confirmed via CDN probing and visual inspection.

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Black          |
| 2                    | White          |
| 4                    | Teal           |
| 5                    | Pink           |

Note: iPhone 16 has 5 colors (Black, White, Teal, Pink, Ultramarine). Ultramarine was not
found in the CDN probe (tested IDs 1-40 across multiple CDN versions). It likely uses ID 9
(the traditional "blue" slot) but the CDN images had not been updated at the time of this
probe. If your device reports DeviceEnclosureColor=9 on an iPhone 16, it is most likely
**Ultramarine**.

### iPhone 16 Pro / 16 Pro Max (iPhone17,3 / iPhone17,4)

Confirmed via CDN probing and visual inspection of large (infobox) images.

| DeviceEnclosureColor | Color Name         |
|----------------------|--------------------|
| 1                    | Black Titanium     |
| 2                    | White Titanium     |
| 4                    | Desert Titanium    |
| 9                    | Natural Titanium   |

Note: The CDN image for Natural Titanium (9) renders with a slight cool/blue tint in the
Find My device artwork, but this maps to the warm gray "Natural Titanium" physical color.

### iPhone 17 Pro / 17 Pro Max (iPhone18,1 / iPhone18,2)

| DeviceEnclosureColor | Color Name         |
|----------------------|--------------------|
| 1                    | Cosmic Orange      |
| 2                    | Silver             |
| 9                    | Deep Blue          |

### iPhone 17 (iPhone18,3)

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Black          |
| 2                    | White          |
| 4                    | Lavender       |
| 5                    | Sage           |
| 9                    | Mist Blue      |

### iPhone Air (iPhone18,4)

| DeviceEnclosureColor | Color Name     |
|----------------------|----------------|
| 1                    | Space Black    |
| 2                    | Cloud White    |
| 4                    | Sky Blue       |
| 5                    | Light Gold     |

---

## Summary: Recurring Enclosure Color ID Patterns

Across models, Apple tends to reuse certain ID slots for similar color families:

| ID  | Typical Usage                                                    |
|-----|------------------------------------------------------------------|
| 1   | Dark/Black variant (Space Gray, Black, Midnight, Graphite, Black Titanium) |
| 2   | Light/White variant (Silver, White, Starlight, White Titanium)   |
| 3   | Gold (on Pro models: iPhone 7-8, 12 Pro, 13 Pro, 14 Pro)        |
| 4   | Warm accent (Rose Gold on 7, Gold on XS/11 Pro, Pink on 13/15, Desert Titanium on 16 Pro, Teal on 16) |
| 5   | Special variant (Jet Black on 7, Natural Titanium on 15 Pro, Pink on 16) |
| 6   | (PRODUCT)RED (consistent across most standard/budget models)     |
| 7   | Yellow (XR, 11, 14, 15)                                         |
| 8   | Coral (XR only)                                                  |
| 9   | Blue family (Blue on XR/12/13/14/15, Sierra Blue/Pacific Blue on Pro, Blue Titanium on 15 Pro, Natural Titanium on 16 Pro) |
| 11  | Purple (iPhone 11)                                               |
| 12  | Green (iPhone 11, 11 Pro Midnight Green, 12/12 mini Green)      |
| 17  | Later-added or special color (Purple on 12 mini/14, Yellow on 14, Deep Purple on 14 Pro) |
| 18  | Later-added color (Green on 13/13 mini/13 Pro Alpine Green, Green on 15) |

**WARNING:** These patterns are approximate generalizations. Always use the model-specific
mapping above. The same ID means different colors on different models.

---

## How to Use

Given a device with:
- `ProductType` = `iPhone16,1`
- `DeviceEnclosureColor` = `1`

1. Look up ProductType: iPhone16,1 = iPhone 15 Pro
2. Look up enclosure color 1 in the iPhone 15 Pro table: **Black Titanium**

Given a device with:
- `ProductType` = `iPhone14,5`
- `DeviceEnclosureColor` = `4`

1. Look up ProductType: iPhone14,5 = iPhone 13
2. Look up enclosure color 4 in the iPhone 13 table: **Pink**

---

## Verification Method

The enclosure color IDs were verified by probing Apple's iCloud Find My device image CDN:

```
https://statici.icloud.com/fmipmobile/deviceImages-9.0/iPhone/{ProductType}-{DeviceColor}-{DeviceEnclosureColor}-0/online-sourcelist__3x.png
```

A valid color returns a unique device image (~19-26 KB). An invalid color returns a
generic fallback image (269,645 bytes). Images were then visually inspected to confirm
color identity.

## Sources

- libimobiledevice issue #818: https://github.com/libimobiledevice/libimobiledevice/issues/818
- libimobiledevice issue #1391: https://github.com/libimobiledevice/libimobiledevice/issues/1391
- iCloud device image URL format (insidegui gist): https://gist.github.com/insidegui/a18124c0c573a4eb656f5c485ea7dae4
- Apple device model list (adamawolf gist): https://gist.github.com/adamawolf/3048717
- FutureTap DeviceColors blog: https://www.futuretap.com/blog/device-colors
- FutureTap DeviceColors repo: https://github.com/futuretap/DeviceColors
- Tribruin iPhoneModelInfo: https://github.com/Tribruin/iPhoneModelInfo
