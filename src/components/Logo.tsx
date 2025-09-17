interface LogoProps {
  variant?: 'full' | 'compact' | 'icon-only';
  size?: 'sm' | 'md' | 'lg';
  theme?: 'light' | 'dark' | 'auto';
  textColor?: 'light' | 'dark';
  className?: string;
  onClick?: () => void;
}

export function Logo({ 
  variant = 'full', 
  size = 'md', 
  theme = 'auto',
  textColor,
  className = '', 
  onClick 
}: LogoProps) {
  const sizeClasses = {
    sm: {
      logo: 'h-8 w-auto',
      text: 'text-lg',
    },
    md: {
      logo: 'h-10 w-auto sm:h-12',
      text: 'text-xl sm:text-2xl',
    },
    lg: {
      logo: 'h-12 w-auto sm:h-16',
      text: 'text-2xl sm:text-3xl',
    },
  };

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      // Default behavior: navigate to home
      window.history.pushState({}, "", "/");
      window.dispatchEvent(new PopStateEvent("popstate"));
    }
  };

  // Determinar las clases CSS y las imágenes según el tema
  const getImageClasses = () => {
    // Determinar el color del texto
    let finalTextClass;
    if (textColor === 'light') {
      finalTextClass = 'text-white';
    } else if (textColor === 'dark') {
      finalTextClass = 'text-gray-900';
    } else {
      // Si no se especifica textColor, usar el comportamiento por defecto basado en el tema
      if (theme === 'light') {
        finalTextClass = 'text-gray-900';
      } else if (theme === 'dark') {
        finalTextClass = 'text-white';
      } else {
        finalTextClass = 'text-gray-900 dark:text-white';
      }
    }

    if (theme === 'light') {
      // Landing page (fondo claro) - usar logo oscuro
      return {
        logoSrc: '/assets/logos/pss-dark.png',
        logoClass: `${sizeClasses[size].logo}`,
        textClass: finalTextClass
      };
    } else if (theme === 'dark') {
      // Dashboard (fondo oscuro) - usar logo claro  
      return {
        logoSrc: '/assets/logos/pss-light.png',
        logoClass: `${sizeClasses[size].logo}`,
        textClass: finalTextClass
      };
    } else {
      // Auto - usar dark mode classes de Tailwind
      return {
        logoSrc: '/assets/logos/pss-dark.png',
        logoClass: `${sizeClasses[size].logo}`,
        textClass: finalTextClass
      };
    }
  };

  const { logoSrc, logoClass, textClass } = getImageClasses();

  if (variant === 'icon-only') {
    return (
      <button
        onClick={handleClick}
        className={`flex items-center justify-center ${className}`}
        aria-label="pseudosapiens home"
      >
        <img 
          src={logoSrc}
          alt="pseudosapiens logo" 
          className={logoClass}
        />
      </button>
    );
  }

  if (variant === 'compact') {
    return (
      <button
        onClick={handleClick}
        className={`flex items-center space-x-2 ${className}`}
        aria-label="pseudosapiens home"
      >
        <img 
          src={logoSrc}
          alt="pseudosapiens logo" 
          className={logoClass}
        />
        <span className={`font-bold tracking-tight ${sizeClasses[size].text} ${textClass}`}>
          pseudosapiens
        </span>
      </button>
    );
  }

  // Full variant (default)
  return (
    <button
      onClick={handleClick}
      className={`flex items-center space-x-3 ${className}`}
      aria-label="pseudosapiens home"
    >
      <img 
        src={logoSrc}
        alt="pseudosapiens logo" 
        className={logoClass}
      />
      <span className={`font-bold tracking-tight ${sizeClasses[size].text} ${textClass}`}>
        pseudosapiens
      </span>
    </button>
  );
}