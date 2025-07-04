import React from 'react';

// material-ui
import Avatar from '@mui/material/Avatar';

// ==============================|| CUSTOM LOGO COMPONENT ||============================== //

const Logo = () => (
    <Avatar
        src="/static/images/logo.png"
        alt="Sonic"
        title="Sonic"
        sx={{ width: 100, height: 100 }}
    />
);

export default Logo;
