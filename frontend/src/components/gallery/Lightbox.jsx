import YARLightbox from 'yet-another-react-lightbox';
import 'yet-another-react-lightbox/styles.css';

export default function Lightbox({ slides, open, onClose, index = 0 }) {
  return (
    <YARLightbox
      open={open}
      close={onClose}
      index={index}
      slides={slides}
    />
  );
}
