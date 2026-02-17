import { useState } from 'react';
import Lightbox from './Lightbox';

export default function PhotoGallery({ photos = [] }) {
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState(0);

  if (!photos || photos.length === 0) return null;

  const slides = photos.map((photo) => ({
    src: photo.url,
    alt: photo.caption || '',
  }));

  const openLightbox = (index) => {
    setLightboxIndex(index);
    setLightboxOpen(true);
  };

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {photos.map((photo, index) => (
          <button
            key={index}
            type="button"
            onClick={() => openLightbox(index)}
            className="aspect-video rounded-lg overflow-hidden bg-gray-200 hover:opacity-90 transition-opacity focus:outline-none focus:ring-2 focus:ring-campfire-500 focus:ring-offset-2"
          >
            <img
              src={photo.url}
              alt={photo.caption || `Photo ${index + 1}`}
              loading="lazy"
              className="w-full h-full object-cover"
            />
          </button>
        ))}
      </div>

      <Lightbox
        slides={slides}
        open={lightboxOpen}
        onClose={() => setLightboxOpen(false)}
        index={lightboxIndex}
      />
    </div>
  );
}
