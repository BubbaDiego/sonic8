
import { useState } from 'react';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import FormControl from 'ui-component/extended/Form/FormControl';
import FormControlSelect from 'ui-component/extended/Form/FormControlSelect';

export default function ProviderAccordion({title, fields, values, onChange}) {
  const handleField = (key, val) => {
    onChange(prev => ({ ...prev, [key]: val }));
  };
  return (
    <Accordion sx={{ mb:2 }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography variant="h6">{title}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Grid container spacing={2}>
          {fields.map(({key,label,type='text',placeholder, selectOptions})=>(
            <Grid item xs={12} md={6} key={key}>
              {selectOptions ? (
                <FormControlSelect
                  captionLabel={label}
                  selected={values?.[key] || ''}
                  currencies={selectOptions}
                  onChange={(e)=>handleField(key,e.target.value)}
                />
              ) : (
                <FormControl
                  captionLabel={label}
                  placeholder={placeholder}
                  formState=""
                  value={values?.[key] || ''}
                  onChange={(e)=>handleField(key,e.target.value)}
                />
              )}
            </Grid>
          ))}
        </Grid>
      </AccordionDetails>
    </Accordion>
  )
}
