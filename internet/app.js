function doGet() {
    return HtmlService.createHtmlOutputFromFile('index.html'); // Загружаем HTML файл
  }
  
  function getAllDataWithImages() {
    const sheetId = "19ON_2opSuF8pMwiqkCnXaTgPTxAobROY1FN3VPYbWiM";
    const sheetName = "form data";
    
    const sheet = SpreadsheetApp.openById(sheetId).getSheetByName(sheetName);
    
    // Проверка существования листа
    if (!sheet) {
      throw new Error(`Sheet with name "${sheetName}" not found.`);
    }
  
    const data = sheet.getDataRange().getValues();
    
    // Проверка наличия данных
    if (data.length <= 1) {
      throw new Error("No data found in the sheet.");
    }
  
    // Удаляем первую строку (заголовки)
    data.shift();
  
    // Формируем данные для отправки в HTML
    return data.map(row => ({
      title: row[1] || '',        // Название товара
      price: row[2] || '',        // Цена товара
      sizes: row[3] ? row[3].split(',') : [], // Размеры товара, ожидается, что они разделены запятыми
      colors: row[4] ? row[4].split(',') : [], // Цвета товара, ожидается, что они разделены запятыми
      image: row[6] || '',        // Ссылка на изображение (обновите индекс, если необходимо)
      description: row[5] || ''    // Описание (обновите индекс, если необходимо)
    }));
  }
  