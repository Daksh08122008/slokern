import React, { useState, useEffect } from 'react';

interface ScrollEdgeToolbarProps {
  children: React.ReactNode;
  scrollThreshold?: number;
}

export const ScrollEdgeToolbar: React.FC<ScrollEdgeToolbarProps> = ({
  children,
  scrollThreshold = 8,
}) => {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const mainEl = document.getElementById('main-content');
    const target = mainEl || window;

    const handleScroll = () => {
      const scrollY = mainEl ? mainEl.scrollTop : window.scrollY;
      setIsScrolled(scrollY > scrollThreshold);
    };

    target.addEventListener('scroll', handleScroll, { passive: true });
    return () => target.removeEventListener('scroll', handleScroll);
  }, [scrollThreshold]);

  return (
    <div
      className={`scroll-edge-toolbar ${isScrolled ? 'scrolled' : 'at-rest'}`}
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 30,
        padding: '10px 24px',
        backgroundColor: isScrolled
          ? 'var(--glass-chrome, rgba(14, 18, 15, 0.72))'
          : 'transparent',
        backdropFilter: isScrolled ? 'blur(16px)' : 'none',
        borderBottom: '1px solid',
        borderColor: isScrolled ? 'var(--border, #263124)' : 'transparent',
        transition: 'background-color 220ms ease, border-color 220ms ease, backdrop-filter 220ms ease',
      }}
    >
      {children}
    </div>
  );
};
