# Redwood React Wireframe

Simple React wireframe for Proviso-style flow:
- Left panel: chat interface for infrastructure requirements and refinements.
- Right panel: editable Terraform draft.

## Files

- `RedwoodInfraWorkbench.jsx`
- `redwood-infra-workbench.css`

## Quick use

Import the component in your React app:

```jsx
import RedwoodInfraWorkbench from "./wireframes/redwood-react-wireframe/RedwoodInfraWorkbench";

export default function App() {
  return <RedwoodInfraWorkbench />;
}
```

The component already imports its CSS:

```jsx
import "./redwood-infra-workbench.css";
```

## Notes

- This is a wireframe, not a production data flow.
- Chat actions currently apply mocked Terraform changes in-browser.
- Replace `applyInfraChange(...)` with your backend call to `/api/v1/generate` or follow-up refinement APIs.
