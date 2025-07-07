// src/views/traderShop/index.jsx
import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import TraderShopList from './TraderShopList';

function TraderShopIndex() {
  return (
    <Routes>
      <Route index element={<TraderShopList />} />
      <Route path="*" element={<Navigate to="." />} />
    </Routes>
  );
}

export default TraderShopIndex;
