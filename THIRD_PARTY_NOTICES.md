# Third-party notices

This skill bundles the following third-party components (inlined into generated HTML so
that diagrams render fully offline). Each is used under its own license.

| Component | Version | License | Bundled as |
|-----------|---------|---------|------------|
| [Cytoscape.js](https://github.com/cytoscape/cytoscape.js) | 3.34.0 | MIT | `assets/cytoscape.min.js` |
| [elkjs](https://github.com/kieler/elkjs) | 0.11.1 | EPL-2.0 | `assets/elk.bundled.js` |
| [cytoscape.js-elk](https://github.com/cytoscape/cytoscape.js-elk) | 2.3.0 | MIT | `assets/cytoscape-elk.js` |
| [Simple Icons](https://github.com/simple-icons/simple-icons) | 16.24.0 | CC0-1.0 | `assets/simple-icons.json` |

Notes:

- **Cytoscape.js** and **cytoscape.js-elk** are MIT-licensed; their license headers are
  preserved inline in the respective minified files.
- **elkjs** is licensed under the Eclipse Public License 2.0 (EPL-2.0). The full license
  header is preserved inline in `assets/elk.bundled.js`. Source:
  <https://github.com/kieler/elkjs>.
- **Simple Icons** icon data is released under CC0-1.0 (public domain). The bundled
  `assets/simple-icons.json` is a consolidated extract (SVG path + brand color per slug).
  The original license and disclaimer are included as
  `assets/simple-icons-LICENSE.md` and `assets/simple-icons-DISCLAIMER.md`.
  **Brand icons remain the trademarks of their respective owners** and are used here only
  as identifying marks; their inclusion does not imply any affiliation or endorsement.

No third-party component is fetched at runtime — everything is vendored on disk and
inlined, which is what makes the zero-egress guarantee hold. To re-vendor any of these
offline, see `references/zero-egress.md`.
