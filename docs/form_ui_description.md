# Forms UI Map and Descriptions

This document maps out the contents of `frontend/src/views/forms` and provides a short description for every file.

## Repository Map

```txt
forms/
├── forms-validation/
│   ├── AutocompleteForms.jsx
│   ├── CheckboxForms.jsx
│   ├── InstantFeedback.jsx
│   ├── LoginForms.jsx
│   ├── RadioGroupForms.jsx
│   ├── SelectForms.jsx
│   └── index.jsx
├── chart/
│   ├── Apexchart/
│   │   ├── ApexAreaChart.jsx
│   │   ├── ApexBarChart.jsx
│   │   ├── ApexColumnChart.jsx
│   │   ├── ApexLineChart.jsx
│   │   ├── ApexMixedChart.jsx
│   │   ├── ApexPieChart.jsx
│   │   ├── ApexPolarChart.jsx
│   │   ├── ApexRedialChart.jsx
│   │   └── index.jsx
│   └── OrgChart/
│       ├── Card.jsx
│       ├── DataCard.jsx
│       ├── LinkedIn.jsx
│       ├── MeetIcon.jsx
│       ├── SkypeIcon.jsx
│       └── index.jsx
├── forms-wizard/
│   ├── index.jsx
│   ├── ValidationWizard/
│   │   ├── AddressForm.jsx
│   │   ├── PaymentForm.jsx
│   │   ├── Review.jsx
│   │   └── index.jsx
│   └── BasicWizard/
│       ├── AddressForm.jsx
│       ├── PaymentForm.jsx
│       ├── Review.jsx
│       └── index.jsx
├── tables/
│   ├── TableBasic.jsx
│   ├── TableCollapsible.jsx
│   ├── TableData.jsx
│   ├── TableDense.jsx
│   ├── TableEnhanced.jsx
│   ├── TableExports.jsx
│   ├── TableStickyHead.jsx
│   └── TablesCustomized.jsx
├── data-grid/
│   ├── QuickFilter/
│   │   ├── CustomFilter.jsx
│   │   ├── ExcludeHiddenColumns.jsx
│   │   ├── Initialize.jsx
│   │   ├── ParsingValues.jsx
│   │   └── index.jsx
│   ├── ColumnVirtualization/
│   │   ├── Virtualization.jsx
│   │   └── index.jsx
│   ├── InLineEditing/
│   │   ├── AutoStop.jsx
│   │   ├── ConfirmationSave.jsx
│   │   ├── Controlled.jsx
│   │   ├── CustomEdit.jsx
│   │   ├── DisableEditing.jsx
│   │   ├── EditableColumn.jsx
│   │   ├── EditableRow.jsx
│   │   ├── EditingEvents.jsx
│   │   ├── FullFeatured.jsx
│   │   ├── ParserSetter.jsx
│   │   ├── ServerValidation.jsx
│   │   ├── Validation.jsx
│   │   └── index.jsx
│   ├── ColumnGroups/
│   │   ├── BasicColumnGroup.jsx
│   │   ├── CustomColumnGroup.jsx
│   │   └── index.jsx
│   ├── SaveRestoreState/
│   │   ├── InitialState.jsx
│   │   ├── UseGridSelector.jsx
│   │   └── index.jsx
│   ├── ColumnVisibility/
│   │   ├── ControlledVisibility.jsx
│   │   ├── InitializeColumnVisibility.jsx
│   │   ├── VisibilityPanel.jsx
│   │   └── index.jsx
│   ├── DataGridBasic/
│   │   └── index.jsx
│   └── ColumnMenu/
│       ├── AddMenuItem.jsx
│       ├── ColumnMenu.jsx
│       ├── CustomMenu.jsx
│       ├── DisableMenu.jsx
│       ├── HideMenuItem.jsx
│       ├── OverrideMenu.jsx
│       ├── ReorderingMenu.jsx
│       └── index.jsx
├── plugins/
│   ├── AutoComplete.jsx
│   ├── Clipboard.jsx
│   ├── Dropzone.jsx
│   ├── Editor.jsx
│   ├── Mask.jsx
│   ├── Recaptcha.jsx
│   ├── Tooltip.jsx
│   └── Modal/
│       ├── ServerModal.jsx
│       ├── SimpleModal.jsx
│       └── index.jsx
├── components/
│   ├── AutoComplete.jsx
│   ├── Button.jsx
│   ├── Checkbox.jsx
│   ├── Radio.jsx
│   ├── Switch.jsx
│   ├── TextField.jsx
│   ├── Slider/
│   │   ├── BasicSlider.jsx
│   │   ├── DisableSlider.jsx
│   │   ├── LabelSlider.jsx
│   │   ├── PopupSlider.jsx
│   │   ├── StepSlider.jsx
│   │   ├── VerticalSlider.jsx
│   │   ├── VolumeSlider.jsx
│   │   └── index.jsx
│   └── DateTime/
│       ├── CustomDateTime.jsx
│       ├── LandscapeDateTime.jsx
│       ├── ViewRendererDateTime.jsx
│       ├── ViewsDateTimePicker.jsx
│       └── index.jsx
└── layouts/
    ├── ActionBar.jsx
    ├── Layouts.jsx
    ├── MultiColumnForms.jsx
    └── StickyActionBar.jsx
```

## File Descriptions

### forms-validation
- **AutocompleteForms.jsx** – Form using Material‑UI Autocomplete with Formik validation.
- **CheckboxForms.jsx** – Checkbox validation example.
- **InstantFeedback.jsx** – Shows real‑time validation messages.
- **LoginForms.jsx** – Sample login form with validation logic.
- **RadioGroupForms.jsx** – Radio group validation example.
- **SelectForms.jsx** – Select component validation demo.
- **index.jsx** – Entry point bundling all validation form demos.

### chart
- **Apexchart/** – Charts built with ApexCharts (line, bar, pie, etc.).
- **OrgChart/** – Components demonstrating a simple organization chart.

### forms-wizard
- **index.jsx** – Wrapper page for multi‑step form examples.
- **ValidationWizard/** – Wizard with validation for each step.
- **BasicWizard/** – Basic stepper form without validation logic.

### tables
- **TableBasic.jsx** – Minimal table example.
- **TableCollapsible.jsx** – Table rows that can expand/collapse.
- **TableData.jsx** – Data table with sorting and pagination.
- **TableDense.jsx** – Dense (compact) table layout.
- **TableEnhanced.jsx** – Enhanced table with selection and sorting.
- **TableExports.jsx** – Demonstrates exporting table data.
- **TableStickyHead.jsx** – Table with a sticky header.
- **TablesCustomized.jsx** – Customized table styling.

### data-grid
- **QuickFilter/** – Examples of the DataGrid quick filter API.
- **ColumnVirtualization/** – Demonstrates virtualized columns.
- **InLineEditing/** – Various approaches for editing grid rows inline.
- **ColumnGroups/** – Grouping header columns.
- **SaveRestoreState/** – Saving and restoring grid state.
- **ColumnVisibility/** – Controlling column visibility.
- **DataGridBasic/** – Basic usage of the MUI DataGrid.
- **ColumnMenu/** – Customizing the column menu actions.

### plugins
- **AutoComplete.jsx** – Async autocomplete plugin.
- **Clipboard.jsx** – Clipboard utilities example.
- **Dropzone.jsx** – Drag‑and‑drop upload zone.
- **Editor.jsx** – Rich text editor field.
- **Mask.jsx** – Input masking plugin demo.
- **Recaptcha.jsx** – Google reCAPTCHA integration.
- **Tooltip.jsx** – Tooltip plugin example.
- **Modal/** – Simple and server‑driven modal dialogs.

### components
- **AutoComplete.jsx** – Basic autocomplete field component.
- **Button.jsx** – Demo of different button types.
- **Checkbox.jsx** – Checkbox field component.
- **Radio.jsx** – Radio button field component.
- **Switch.jsx** – Toggle switch component.
- **TextField.jsx** – Text input field variations.
- **Slider/** – Range slider variations (basic, labeled, vertical, etc.).
- **DateTime/** – Date/time picker examples.

### layouts
- **ActionBar.jsx** – Toolbar layout for form actions.
- **Layouts.jsx** – Wrapper showcasing different form layouts.
- **MultiColumnForms.jsx** – Multi‑column form grid.
- **StickyActionBar.jsx** – Sticky footer bar with actions.
