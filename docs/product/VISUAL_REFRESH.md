# Visual refinement and README illustrations

This revision refines the existing family and small-institution interface. It keeps the current product flows and makes the hierarchy, spacing, typography, navigation and surface treatments more consistent.

## Design direction

- A warm paper background, deep green text and restrained forest-green actions give the interface a calm, familiar tone. Sage and soft peach distinguish supporting surfaces without replacing written labels.
- Japanese system fonts, comfortable line height, lighter dividers and consistent rounded controls make short tasks easier to scan. Primary actions remain visually stronger than optional settings and supplementary details.
- Home centers the existing **current baby and sharing choice → quick record → recent records** flow. Record status, correction and unresolved operations remain visible in their relevant context.
- AI questions and human support retain distinct labels. Family sharing stays an explicit choice; visual styling does not change permissions or consent.
- Institution maintenance continues to distinguish local changes, saved drafts, publication preview and explicitly published information.

## README illustrations

The two illustrations are self-contained SVG source files. Illustrated shortcuts are an example of the existing configurable selection, rather than a fixed default:

| Illustration | What it explains |
| --- | --- |
| [Family desktop and phone](../assets/family-ui-overview.svg) | The Home information hierarchy, labelled navigation, private recording scope and recent personal records. |
| [Small institution](../assets/organization-ui-overview.svg) | Contact maintenance, one-at-a-time review and the separate preview/publication steps. |

**UIデザインの模式図・架空の例。実行画面のスクリーンショットではありません。**

These are design illustrations of the current product structure, not application screenshots or evidence of runtime verification. Content has been condensed for a readable overview; actual layouts depend on the viewport, current state, language and display settings. The family desktop uses the product's five horizontal navigation tabs; the phone keeps the same five tabs at the bottom. Both examples show four configurable shortcuts in two columns, a Japan-time example date and the current green Baby mark with a peach leaf. The institution illustration combines existing maintenance and publication concepts; action availability still follows the application's actual validation and review state.

The baby nickname, record values, times and service names are fictional. No real account, family record, contact information, IP address, authentication token or medical credential is included. The SVG files use local system font stacks and contain no external images, remote fonts, executable scripts or embedded tracking resources. Japanese glyph appearance depends on fonts installed on the viewing device.

## Verification boundary

The application, dependency installation, build, tests, lint, parsers, migration and browser were not run for this revision. The SVG files were authored directly as repository assets; they were not generated from a running interface. Their rendered appearance and the application's rendered appearance have not been verified.

When runtime work is authorized, review narrow phones, Japanese wrapping, large text, keyboard focus, high contrast and reduced motion; then check record/save states, visible sharing scope, navigation, institution draft/preview/publication separation and README image rendering. Existing [UI foundation contracts](UI_FOUNDATION.md) and [UI architecture](UI_REFINEMENT.md) remain applicable.
