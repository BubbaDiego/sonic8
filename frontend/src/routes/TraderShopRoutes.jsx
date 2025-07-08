// src/routes/TraderShopRoutes.jsx
import React from 'react';
import { Navigate } from 'react-router-dom';
import Loadable from 'ui-component/Loadable';
import MainLayout from 'layout/MainLayout';

//const TraderShop = Loadable(() => import('views/traderShop'));
import TraderShop from 'views/traderShop';


const TraderShopRoutes = {
  path: '/trader-shop',
  element: <MainLayout />,
  children: [
    {
      path: '',
      element: <TraderShop />
    },
    {
      path: '*',
      element: <Navigate to="/trader-shop" />
    }
  ]
};

export default TraderShopRoutes;
