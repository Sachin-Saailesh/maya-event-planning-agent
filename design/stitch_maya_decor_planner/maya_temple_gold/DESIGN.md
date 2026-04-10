# Design System Specification: The Ethereal Concierge

## 1. Overview & Creative North Star
**The Creative North Star: "The Digital Silk Loom"**
This design system is a marriage of heritage and high-tech. It rejects the sterile, "boxy" nature of traditional SaaS in favor of a cinematic, editorial experience. We are weaving the intricate, tactile luxury of a South Indian wedding—think Kanjeevaram textures and temple gold—with the fluid, ephemeral nature of advanced AI.

The goal is to move away from "templates" and toward "compositions." We achieve this through:
*   **Intentional Asymmetry:** Breaking the grid with overlapping glass panels.
*   **Atmospheric Depth:** Using "glows" rather than "shadows" to simulate light passing through silk.
*   **Motion as Meaning:** Every state change should feel like a camera lens focusing or a silk drape settling.

---

## 2. Colors & Surface Philosophy
The palette is rooted in the depth of a midnight sky, illuminated by the warmth of ritual gold and soft rose.

### The "No-Line" Rule
**Explicit Instruction:** Do not use 1px solid borders to define sections. Boundaries must be felt, not seen. Define separation through background color shifts (e.g., a `surface-container-low` card resting on a `surface` background) or subtle tonal transitions.

### Surface Hierarchy & Nesting
Treat the UI as a physical space. 
*   **Base:** `surface` (#131313) is your floor.
*   **Plinth:** Use `surface-container-low` for large, structural sections.
*   **Object:** Use `surface-container-high` or `highest` for interactive cards.
*   **Nesting:** To create focus, nest a `surface-container-lowest` element inside a `surface-container` block. This "inverted depth" creates a sophisticated, recessed look.

### The Glass & Gradient Rule
*   **Glassmorphism:** Use for floating panels (e.g., Voice Transcript). Apply `surface` with 60% opacity and a `20px to 40px` backdrop-blur. 
*   **Signature Gradients:** For primary CTAs, use a linear gradient from `primary` (#f2ca50) to `primary_container` (#d4af37). This mimics the sheen of polished gold.

---

## 3. Typography: Editorial Authority
We utilize a high-contrast pairing to balance tradition and utility.

*   **Display & Headlines:** `notoSerif`. This is our "Heritage" voice. Use it sparingly for poetic moments, titles, and emotional hooks. It should feel like an invitation.
*   **Body & Labels:** `manrope`. This is our "Intelligence" voice. Clean, geometric, and highly legible, representing the precision of the AI.

**Hierarchy Strategy:** 
Use `display-lg` for hero statements but keep `body-md` for the bulk of data. The massive scale difference between a `display` title and a `label-sm` metadata tag creates the "High-End Editorial" feel.

---

## 4. Elevation & Depth
We replace traditional shadows with **Tonal Layering** and **Ambient Glows.**

*   **The Layering Principle:** Place a `surface-container-lowest` card on a `surface-container-low` section to create a soft, natural "lift" through contrast alone.
*   **Ambient Glows:** When an element must float (like a voice modal), use a shadow tinted with `on_secondary` (#4a0080) at 5% opacity. Blur should be extreme (80px+) to mimic the glow of a screen in a dark room.
*   **The Ghost Border:** If accessibility requires a border, use `outline_variant` at **15% opacity**. This provides a "suggestion" of a boundary without breaking the cinematic immersion.

---

## 5. Components

### The Waveform (AI Voice State)
Instead of a simple bar, use fluid, overlapping SVG paths using the `secondary` (#ddb7ff) and `tertiary` (#e9c7c0) colors. Apply a `screen` blend mode where they overlap to create a luminous, "Gemini-inspired" shimmer.

### Primary Buttons (Gold Leaf)
*   **Style:** `primary` background with `on_primary` text.
*   **Shape:** `full` (pill-shaped) for a modern, friendly feel.
*   **Refinement:** A subtle inner-glow (1px white at 10% opacity) on the top edge to give the button a "minted" gold coin appearance.

### Transcript Bubbles (The Loom)
*   **User:** `surface-container-highest` with `on_surface` text. Right-aligned.
*   **AI:** Glassmorphic (semi-transparent `secondary_container`) with `on_secondary_container` text. Left-aligned.
*   **Spacing:** Generous vertical rhythm; no dividers between messages.

### Hall Selection Cards (Immersive)
*   **Structure:** Edge-to-edge photography with a `surface_container_lowest` footer. 
*   **Interaction:** On hover, the image should scale 5% while a subtle `primary` (gold) glow emanates from beneath the card.

### Inputs (The Ivory Field)
*   **Style:** No background box. Use a `ghost border` bottom-only line. 
*   **Focus:** The bottom line transitions from `outline` to a `primary` (gold) gradient.

---

## 6. Do’s and Don’ts

### Do
*   **Do** use extreme whitespace. If a section feels "full," it is likely too crowded.
*   **Do** use `notoSerif` for numbers in wedding dates to make them feel like milestones.
*   **Do** use `secondary_container` (purple) as a very subtle background glow behind important glass cards to add "soul."

### Don’t
*   **Don’t** use pure `#000000` for text; use `on_surface` to maintain a soft, premium feel.
*   **Don’t** use 90-degree corners for cards; always use the `xl` (0.75rem) or `lg` (0.5rem) roundedness to keep the mood "warm."
*   **Don’t** use standard blue for links. Use `tertiary` (#e9c7c0) or `primary` (#f2ca50).
*   **Don’t** use "Drop Shadows." If an object needs to pop, use a **Tonal Shift** or an **Ambient Glow**.