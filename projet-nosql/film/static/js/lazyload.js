document.addEventListener('DOMContentLoaded', function () {
  function loadImg(img) {
    var src = img.getAttribute('data-src');
    if (!src) return;
    img.onload = function () { img.classList.add('loaded'); };
    img.setAttribute('src', src);
  }

  var imgs = document.querySelectorAll('img.lazy-img[data-src]');
  imgs.forEach(function (img) {
    if ('IntersectionObserver' in window) {
      var observer = new IntersectionObserver(function (entries, obs) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            loadImg(entry.target);
            obs.unobserve(entry.target);
          }
        });
      }, { rootMargin: '100px' });
      observer.observe(img);
    } else {
      loadImg(img);
    }
  });
});