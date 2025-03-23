function updateValue(value) {
    document.getElementById('rangeValue').textContent = value;
}


// Пример JavaScript для переключения изображений
const mainImage = document.querySelector('.main-image');
const thumbnails = document.querySelectorAll('.thumbnail');

thumbnails.forEach(thumbnail => {
  thumbnail.addEventListener('click', () => {
    mainImage.src = thumbnail.src;
  });
});

