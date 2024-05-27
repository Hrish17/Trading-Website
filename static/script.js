document.addEventListener('DOMContentLoaded', function () {
  const tickButtons = document.querySelectorAll('.tick-button');
  const flashContainer = document.getElementById('flash-message-container');
  const submitButton = document.getElementById('submit-button');
  let tickedCount = 0;
  const maxTickedCount = 5;
  const selectedStocks = [];
  var stockData  = [];

  fetch('/api/stock_list')
  .then(function(response){
    return response.json();
  }).then(function(data){
    stockData = data;
    console.log(stockData);
  }).catch(function(err){
    console.log(err);
  });

  tickButtons.forEach(function (tickButton, index) {
    tickButton.addEventListener('click', function () {
      const isChecked = tickButton.classList.contains('ticked');

      if ((isChecked && tickedCount > 0) || (!isChecked && tickedCount < maxTickedCount)) {
        toggleTick(tickButton, isChecked, index);
      } else if (!isChecked) {
        flashMessage('You already selected the maximum limit (5).');
      }
    });
  });

  submitButton.addEventListener('click', function () {
    // Send selected stocks to Flask backend
    sendSelectedStocksToFlask(selectedStocks);
  });

  function toggleTick(clickedButton, isChecked, index) {
    clickedButton.classList.toggle('ticked');

    // Update ticked count based on the operation
    tickedCount += isChecked ? -1 : 1;

    const newIsChecked = clickedButton.classList.contains('ticked');
    clickedButton.innerHTML = newIsChecked ? '&#10003;' : '';

    // Update selected stocks array
    const selectedStock = stockData[index].Symbol;

    if (newIsChecked) {
      selectedStocks.push(selectedStock);
    } else {
      const stockIndex = selectedStocks.findIndex(stock => stock.Symbol === selectedStock.Symbol);
      if (stockIndex !== -1) {
        selectedStocks.splice(stockIndex, 1);
      }
    }

    // Log the selected stocks (you can replace this with your desired logic)
    console.log('Selected Stocks:', selectedStocks);
  }


  function sendSelectedStocksToFlask(selectedStocks) {
    fetch('/api/save_selected_stocks', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ selectedStocks: selectedStocks }),
    })
      .then(function (response) {
        return response.json();
      })
      .then(function (data) {
        console.log('Response from Flask:', data);
        // redirect to the results page
        window.location.href = '/compare_graph';
      })
      .catch(function (err) {
        console.error('Error sending data to Flask:', err);
      });
  }



  function flashMessage(message) {
    flashContainer.innerText = message;
    flashContainer.style.opacity = '1';
    flashContainer.style.display = 'block';

    setTimeout(function () {
      flashContainer.style.opacity = '0';
      setTimeout(function () {
        flashContainer.style.display = 'none';
      }, 500);
    }, 2000);
  }

});
