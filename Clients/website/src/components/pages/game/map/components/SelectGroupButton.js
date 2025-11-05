import * as React from 'react';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';

export default function SelectGroupButton({categories, select, setSelect}) {

    const handleSelection = (event, select) => {
        if (select!== null)setSelect(select);
    };
    return (
        <ToggleButtonGroup
            value={select}
            exclusive
            onChange={handleSelection}
        >
            {categories.map((category, index) => <ToggleButton key={index} value={index}> {category} </ToggleButton>)}
        </ToggleButtonGroup>
    );
}
