# ✅ test_out_of_stock_excluded_from_results

**Domain:** Product Search  
**Date:** 2026-05-25

---

## What this test checks

> OOS-TEST has the 'Hiking' tag but inventory=0.  It must never appear in
> search results regardless of the query.

> DB assertion: no mutations.

> PASS criteria
> -------------
> - search_products called.
> - OOS-TEST SKU absent from every search_products result.
> - 'Perpetually Out-of-Stock Widget' absent from the reply.

## Outcome

**PASSED** — all assertions met.

## Conversation

> **User:** Show me all your hiking products

**🔧 `search_products`**

**Args:**
```json
{
  "tags": [
    "Hiking"
  ]
}
```

**Result:**
```json
[
  {
    "sku": "SOCS005",
    "name": "AirHaven Ultralight Hammock",
    "price": 44.99,
    "description": "Lightweight parachute-nylon hammock that packs to the size of a fist. Straps included \u2014 sets up between any two trees in minutes for a camp nap or an ultralight overnight.",
    "tags": "Camping, Hammock, Hiking, Ultralight"
  },
  {
    "sku": "SOAP025",
    "name": "AlpineGuard Knee-High Mountaineering Gaiters",
    "price": 59.99,
    "description": "Full knee-high waterproof gaiters for deep snow, mud, and stream crossings. Nylon shell with taped seams, instep strap, and front lace hook keep them locked down on steep terrain. Work over any tall hiking or mountaineering boot.",
    "tags": "Apparel, Footwear, Hiking, Mountaineering, Snow, Winter"
  },
  {
    "sku": "SOAP010",
    "name": "AlpineGuard Low-Cut Trail Gaiters",
    "price": 34.99,
    "description": "Lightweight gaiters that keep debris, mud, and snow out of your shoes on the trail. Velcro closure, instep strap, and elastic binding fit most trail runners and mid-height hiking boots.",
    "tags": "Apparel, Footwear, Hiking, Snow, Trail Running"
  },
  {
    "sku": "SOCL015",
    "name": "ApproachPro Climbing Approach Shoes",
    "price": 109.99,
    "description": "Sticky rubber approach shoes that grip slabs and scrambles as well as the walk-in trail. Rand wraps the toe and heel for protection; a low-profile midsole keeps you close to the rock.",
    "tags": "Climbing, Footwear, Hiking"
  },
  {
    "sku": "SOSN011",
    "name": "BackcountryFloat Technical Snowshoes",
    "price": 219.99,
    "description": "Aggressive 30-inch backcountry snowshoes with a rotating toepiece that reduces calf fatigue on long ascents. Carbon steel crampons bite into steep, icy terrain where recreational shoes slide out.",
    "tags": "Hiking, Mountaineering, Snow, Snowshoes, Winter"
  },
  {
    "sku": "SONT007",
    "name": "BasePoint Orienteering Compass",
    "price": 14.99,
    "description": "Liquid-filled baseplate compass with a magnifying lens, map ruler, and rotating azimuth ring. Accurate and reliable \u2014 the first compass every hiker should own.",
    "tags": "Hiking, Navigation"
  },
  {
    "sku": "SONT010",
    "name": "CarbonStride Carbon Trekking Poles (pair)",
    "price": 134.99,
    "description": "Ultra-stiff carbon fiber trekking poles at just 240g per pair. Flick-lock collars adjust in seconds; extended cork-and-foam grips let you choke up on descents. For fastpackers and trail runners who count grams.",
    "tags": "Hiking, Navigation, Poles, Trail Running, Ultralight"
  },
  {
    "sku": "SONT012",
    "name": "ChargePack 10000mAh Power Bank",
    "price": 44.99,
    "description": "10,000mAh USB-C PD power bank that can fully charge a smartphone three times. Dual USB-A ports allow simultaneous charging of two devices. Compact brick form factor slips into any hip-belt pocket.",
    "tags": "Camping, Hiking, Tech"
  },
  {
    "sku": "SONT016",
    "name": "ChargePack 20000mAh Power Bank",
    "price": 69.99,
    "description": "High-capacity 20,000mAh power bank with 65W USB-C PD output \u2014 fast enough to charge a laptop. Charges a smartphone six times over and runs a GPS device for a full multi-day trip. Dual USB-A ports charge accessories simultaneously.",
    "tags": "Camping, Hiking, Tech"
  },
  {
    "sku": "SONT017",
    "name": "CompactStride Folding Trekking Poles (pair)",
    "price": 79.99,
    "description": "Three-section folding trekking poles that collapse to 35cm \u2014 small enough to strap to a daypack or check in luggage without the bulk of standard telescoping poles. Sturdy enough for technical terrain despite the compact form factor.",
    "tags": "Hiking, Navigation, Poles, Ultralight"
  },
  {
    "sku": "SOAP012",
    "name": "ConvertPro Zip-Off Hiking Pants",
    "price": 74.99,
    "description": "Quick-dry nylon hiking pants that zip off at the knee to become shorts. Four zippered pockets, UPF 30 fabric, and an articulated knees cut provide all-day comfort on trail or in camp.",
    "tags": "Apparel, Backpacking, Hiking"
  },
  {
    "sku": "SOWS005",
    "name": "DrySeal Waterproof Bag 10L",
    "price": 19.99,
    "description": "Roll-top dry bag that keeps gear bone-dry in any conditions. 500D PVC tarpaulin construction with welded seams \u2014 a kayaking and rafting essential that doubles as camp storage.",
    "tags": "Dry Bag, Hiking, Water Sports"
  },
  {
    "sku": "SOWS017",
    "name": "DrySeal Waterproof Bag 20L",
    "price": 27.99,
    "description": "20L roll-top dry bag that splits the difference between the compact 10L and the expedition 30L. Fits a day's worth of clothing, a sleeping bag, or camera gear. Shoulder strap loop makes it wearable as a light daypack.",
    "tags": "Camping, Dry Bag, Hiking, Water Sports"
  },
  {
    "sku": "SOWS016",
    "name": "DrySeal Waterproof Bag 5L",
    "price": 14.99,
    "description": "Compact 5L roll-top dry bag for phones, wallets, keys, and other small valuables on the water. Same welded-seam 500D PVC construction as the larger DrySeal bags \u2014 just right for a hip-belt pocket or the top of a kayak hatch.",
    "tags": "Dry Bag, Hiking, Water Sports"
  },
  {
    "sku": "SOFD007",
    "name": "ElectroPulse Electrolyte Tablets (20-pack)",
    "price": 24.99,
    "description": "Effervescent electrolyte tablets with sodium, potassium, magnesium, and B vitamins. One tablet dissolved in 16 oz of water delivers fast hydration without sugar or artificial dyes.",
    "tags": "Food, Hiking, Hydration, Nutrition, Trail Running"
  },
  {
    "sku": "SOFD008",
    "name": "HydroFlow 2L Insulated Hydration Reservoir",
    "price": 49.99,
    "description": "2-liter insulated hydration reservoir with a bite valve and magnetic tube clip. Thermal insulation keeps water cool for hours on hot-weather hikes \u2014 fits most hydration-compatible packs.",
    "tags": "Food, Hiking, Hydration, Trail Running"
  },
  {
    "sku": "SOFD021",
    "name": "HydroFlow 3L Hydration Reservoir",
    "price": 54.99,
    "description": "3-liter hydration reservoir with a wide-mouth fill port for easy ice loading and a high-flow bite valve. Insulated tube sleeve and magnetic clip keep the hose routed and accessible while you move.",
    "tags": "Backpacking, Food, Hiking, Hydration, Trail Running"
  },
  {
    "sku": "SOFD001",
    "name": "LifeStraw Personal Water Filter",
    "price": 19.99,
    "description": "Hollow-fiber membrane filter that removes 99.999999% of bacteria and 99.999% of protozoa from any freshwater source. Filters up to 4,000 liters \u2014 no batteries, pumping, or chemicals required.",
    "tags": "Food, Hiking, Safety, Ultralight, Water Filter"
  },
  {
    "sku": "SONT015",
    "name": "MidBeam 350-Lumen Headlamp",
    "price": 44.99,
    "description": "Rechargeable 350-lumen headlamp with a 70-meter beam and a red night-vision mode. USB-C charging, IPX6 waterproof, and a single-button interface \u2014 the practical middle ground between ultralight and full-power.",
    "tags": "Camping, Headlamp, Hiking, Lighting, Navigation"
  },
  {
    "sku": "SOAP017",
    "name": "NeckWrap Multifunctional Gaiter",
    "price": 19.99,
    "description": "Stretchy moisture-wicking tube that works as a neck gaiter, balaclava, headband, or dust mask. UPF 50+ polyester fabric \u2014 equally useful on a dusty desert trail or a cold ski resort lift.",
    "tags": "Apparel, Hiking, Snow, Trail Running, Winter"
  },
  {
    "sku": "SONT002",
    "name": "NightForce Pro 800-Lumen Headlamp",
    "price": 79.99,
    "description": "Rechargeable headlamp delivering 800 lumens on turbo with a 120-meter throw. USB-C charging, powerbank output to charge a phone, and a lockout mode to prevent accidental activation in your pack.",
    "tags": "Camping, Headlamp, Hiking, Lighting, Navigation, Tech"
  },
  {
    "sku": "SOAP004",
    "name": "PacificShell Packable Rain Jacket",
    "price": 64.99,
    "description": "2.5-layer waterproof-breathable rain jacket that packs into its own chest pocket. Fully taped seams, a helmet-compatible hood, and pit zips for venting on steep climbs.",
    "tags": "Apparel, Hiking, Jacket, Waterproof"
  },
  {
    "sku": "SOFD020",
    "name": "PumpGuard Pump Water Filter",
    "price": 49.99,
    "description": "Hand-pump filter with a hollow-fiber membrane that removes bacteria, protozoa, and microplastics. Processes 1L per minute with no waiting \u2014 the fast option when you need treated water now, not in five minutes.",
    "tags": "Backpacking, Food, Hiking, Safety, Water Filter"
  },
  {
    "sku": "SOAP001",
    "name": "QuickStep Lightweight Trail Runners",
    "price": 89.99,
    "description": "Breathable mesh trail runners with a rock plate and sticky rubber outsole. Low-profile enough for road runs, aggressive enough for technical singletrack.",
    "tags": "Apparel, Footwear, Hiking, Trail Running"
  },
  {
    "sku": "SOAP018",
    "name": "QuickStep Waterproof Trail Runners",
    "price": 114.99,
    "description": "Gore-Tex waterproof version of the QuickStep trail runner \u2014 same sticky rubber outsole and rock plate, with an added waterproof-breathable membrane for wet trails, stream crossings, and rainy-day runs.",
    "tags": "Apparel, Footwear, Hiking, Trail Running, Waterproof"
  },
  {
    "sku": "SOFD014",
    "name": "RapidFuel Energy Gel Variety Pack (12-pack)",
    "price": 27.99,
    "description": "Twelve 100-kcal energy gels in four flavors \u2014 each with 25g of fast-acting carbohydrates and a small caffeine hit. Isotonic formula requires no extra water and goes down cleanly mid-effort.",
    "tags": "Backpacking, Food, Hiking, Nutrition, Trail Running"
  },
  {
    "sku": "SOAP026",
    "name": "RunningBrim Lightweight Trail Cap",
    "price": 28.99,
    "description": "Featherlight 60g trail running cap with a structured brim, laser-cut vents, and a rear reflective strip. Sweat-wicking headband and an adjustable back strap \u2014 blocks sun without trapping heat.",
    "tags": "Apparel, Hiking, Sun Protection, Trail Running"
  },
  {
    "sku": "SONT004",
    "name": "SatLink Two-Way Satellite Communicator",
    "price": 349.99,
    "description": "Two-way satellite text messaging and GPS tracking device with a dedicated SOS button that alerts rescue services globally. Works anywhere on Earth \u2014 no cell towers required.",
    "tags": "Hiking, Mountaineering, Navigation, Safety, Tech"
  },
  {
    "sku": "SONT008",
    "name": "SightMaster Pro Sighting Compass",
    "price": 49.99,
    "description": "Mirror-sighting compass with declination adjustment, a global needle, and a clinometer for slope measurement. Preferred by mountain guides and search-and-rescue teams for precision backcountry navigation.",
    "tags": "Hiking, Mountaineering, Navigation"
  },
  {
    "sku": "SOSN010",
    "name": "SnowTrek Recreational Snowshoes",
    "price": 119.99,
    "description": "25-inch aluminum-frame snowshoes for packed and moderate powder trails. Simple ratchet bindings fit most winter boots, and the molded crampon keeps you upright on icy slopes.",
    "tags": "Hiking, Snow, Snowshoes, Winter"
  }
]
```

> **Sierra Outfitters:** Here's a list of what we'd pack for your hiking expedition:

- **AirHaven Ultralight Hammock**: $44.99 - Lightweight hammock, perfect for a camp nap or an overnight.
- **AlpineGuard Knee-High Mountaineering Gaiters**: $59.99 - Waterproof gaiters for snow and mud.
- **AlpineGuard Low-Cut Trail Gaiters**: $34.99 - Lightweight gaiters to keep debris out of your shoes.
- **ApproachPro Climbing Approach Shoes**: $109.99 - Shoes that grip for climbing and hiking.
- **BackcountryFloat Technical Snowshoes**: $219.99 - Snowshoes for icy, steep terrain.
- **BasePoint Orienteering Compass**: $14.99 - Perfect for beginners; reliable navigation.
- **CarbonStride Carbon Trekking Poles (pair)**: $134.99 - Super light and adjustable trekking poles.
- **ChargePack 10000mAh Power Bank**: $44.99 - Charges your devices wherever you go.
- **ConvertPro Zip-Off Hiking Pants**: $74.99 - Versatile pants that become shorts.
- **LifeStraw Personal Water Filter**: $19.99 - A must-have for fresh drinking water.
- **MidBeam 350-Lumen Headlamp**: $44.99 - Rechargeable and waterproof headlamp.
- **NightForce Pro 800-Lumen Headlamp**: $79.99 - Powerful with long-range beam.
- **PacificShell Packable Rain Jacket**: $64.99 - Packs small for unexpected rain.
- **PumpGuard Pump Water Filter**: $49.99 - Fast filter for safe drinking water.
- **QuickStep Lightweight Trail Runners**: $89.99 - Great for trail runs and technical hikes.
- **SatLink Two-Way Satellite Communicator**: $349.99 - Stay connected anywhere on the globe.
- **SnowTrek Recreational Snowshoes**: $119.99 - Ready for packed and powder trails.

Feel free to ask if you want more information about any of these items! 🏔️🧭
