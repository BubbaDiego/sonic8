// src/routes/TraderShopRoutes.jsx
import React from 'react';
import Loadable from 'ui-component/Loadable';
import MainLayout from 'layout/MainLayout';

const TraderShopIndex = Loadable(() => import('views/traderShop'));

const TraderShopRoutes = {
  path: '/trader-shop',
  element: <MainLayout />,
  children: [
    {
      path: '',
      element: <TraderShopIndex />
    }
  ]
};

export default TraderShopRoutes;