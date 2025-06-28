import PropTypes from 'prop-types';
import { useEffect, useState } from 'react';

import useMediaQuery from '@mui/material/useMediaQuery';
import Box from '@mui/material/Box';

// third party
import Slider from 'react-slick';

// project imports
import ProductCard from 'ui-component/cards/ProductCard';
import { getRelatedProducts } from 'api/products';

import useConfig from 'hooks/useConfig';

// ==============================|| PRODUCT DETAILS - RELATED PRODUCTS ||============================== //

export default function RelatedProducts({ id }) {
  const { container } = useConfig();
  const [related, setRelated] = useState([]);
  const [itemsToShow, setItemsToShow] = useState(5);
  const downSM = useMediaQuery((theme) => theme.breakpoints.down('sm'));
  const downMD = useMediaQuery((theme) => theme.breakpoints.down('md'));
  const downLG = useMediaQuery((theme) => theme.breakpoints.down('lg'));
  const downXL = useMediaQuery((theme) => theme.breakpoints.down('xl'));
  const upXL = useMediaQuery((theme) => theme.breakpoints.up('xl'));

  const [loader, setLoader] = useState(true);

  useEffect(() => {
    async () => {
      await getRelatedProducts(id).then((response) => {
        setRelated(response.data);
        setLoader(false);
      });
    };
  }, [id]);

  useEffect(() => {
    if (downSM) {
      setItemsToShow(1);
      return;
    }
    if (downMD) {
      setItemsToShow(2);
      return;
    }
    if (downLG) {
      setItemsToShow(3);
      return;
    }
    if (downXL) {
      setItemsToShow(container ? 3 : 4);
      return;
    }
    if (upXL) {
      setItemsToShow(container ? 3 : 5);
    }
  }, [downSM, downMD, downLG, downXL, upXL, itemsToShow, container]);

  const settings = {
    dots: false,
    centerMode: true,
    swipeToSlide: true,
    focusOnSelect: true,
    centerPadding: '0px',
    slidesToShow: itemsToShow
  };

  let productResult = null;
  if (related && !loader) {
    productResult = related.map((product, index) => (
      <Box key={index} sx={{ p: 1.5 }}>
        <ProductCard
          key={index}
          id={product.id}
          image={product.image}
          name={product.name}
          offerPrice={product.offerPrice}
          salePrice={product.salePrice}
          rating={product.rating}
        />
      </Box>
    ));
  }

  return <Slider {...settings}>{productResult}</Slider>;
}

RelatedProducts.propTypes = { id: PropTypes.string };
