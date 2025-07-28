import React from 'react';

// material-ui
import Avatar from '@mui/material/Avatar';

// ==============================|| CUSTOM LOGO COMPONENT ||============================== //

const Logo = () => (
    <Avatar
        src="/images/logo.png"
        alt="Sonic"
        title="Sonic"
        sx={{ width: 40, height: 40 }}
    />
);

export default Logo;
