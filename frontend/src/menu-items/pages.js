// assets
import { IconKey, IconReceipt2, IconBug, IconBellRinging, IconPhoneCall, IconQuestionMark, IconShieldLock } from '@tabler/icons-react';

// constant
const icons = {
  IconKey,
  IconReceipt2,
  IconBug,
  IconBellRinging,
  IconPhoneCall,
  IconQuestionMark,
  IconShieldLock
};

// ==============================|| EXTRA PAGES MENU ITEMS ||============================== //

const pages = {
  id: 'pages',
  title: 'pages',
  caption: 'pages-caption',
  icon: icons.IconKey,
  type: 'group',
  children: [
    {
      id: 'price',
      title: 'pricing',
      type: 'collapse',
      icon: icons.IconReceipt2,
      children: [
        {
          id: 'price1',
          title: 'price 01',
          type: 'item',
          url: '/pages/price/price1'
        },
        {
          id: 'price2',
          title: 'price 02',
          type: 'item',
          url: '/pages/price/price2'
        }
      ]
    },
    {
      id: 'maintenance',
      title: 'maintenance',
      type: 'collapse',
      icon: icons.IconBug,
      children: [
        {
          id: 'error',
          title: 'error-404',
          type: 'item',
          url: '/pages/error',
          target: true
        },
        {
          id: '500',
          title: 'error-500',
          type: 'item',
          url: '/pages/500',
          target: true
        },
        {
          id: 'coming-soon',
          title: 'coming-soon',
          type: 'collapse',
          children: [
            {
              id: 'coming-soon1',
              title: 'coming-soon 01',
              type: 'item',
              url: '/pages/coming-soon1',
              target: true
            },
            {
              id: 'coming-soon2',
              title: 'coming-soon 02',
              type: 'item',
              url: '/pages/coming-soon2',
              target: true
            }
          ]
        },
        {
          id: 'under-construction',
          title: 'under-construction',
          type: 'item',
          url: '/pages/under-construction',
          target: true
        }
      ]
    },
    {
      id: 'landing',
      title: 'landing',
      type: 'item',
      icon: icons.IconBellRinging,
      url: '/pages/landing',
      target: true
    },
    {
      id: 'contact-us',
      title: 'contact-us',
      type: 'item',
      icon: icons.IconPhoneCall,
      url: '/pages/contact-us',
      target: true
    },
    {
      id: 'faqs',
      title: 'faqs',
      type: 'item',
      icon: icons.IconQuestionMark,
      url: '/pages/faqs',
      target: true
    },
    {
      id: 'privacy-policy',
      title: 'privacy-policy',
      type: 'item',
      icon: icons.IconShieldLock,
      url: '/pages/privacy-policy',
      target: true
    }
  ]
};

export default pages;
