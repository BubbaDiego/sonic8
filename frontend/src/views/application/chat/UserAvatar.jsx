import PropTypes from 'prop-types';
// material-ui
import Avatar from '@mui/material/Avatar';
import Badge from '@mui/material/Badge';

// project imports
import AvatarStatus from './AvatarStatus';
import { getImageUrl, ImagePath } from 'utils/getImageUrl';

export default function UserAvatar({ user }) {
  return (
    <Badge
      overlap="circular"
      badgeContent={<AvatarStatus status={user.online_status} />}
      anchorOrigin={{
        vertical: 'bottom',
        horizontal: 'right'
      }}
    >
      <Avatar alt={user.name} src={user.avatar && getImageUrl(`${user.avatar}`, ImagePath.USERS)} />
    </Badge>
  );
}

UserAvatar.propTypes = { user: PropTypes.any };
