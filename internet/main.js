function doPost(e) {
    try {
      const sheetId = "19ON_2opSuF8pMwiqkCnXaTgPTxAobROY1FN3VPYbWiM";
      const sheetName = "form data";
      const sheet = SpreadsheetApp.openById(sheetId).getSheetByName(sheetName);
      
      if (!sheet) {
        return ContentService.createTextOutput(JSON.stringify({ status: 'error', message: 'Sheet not found' }))
                             .setMimeType(ContentService.MimeType.JSON);
      }
  
      // Validate incoming parameters
      const productId = e.parameter.productId || '';
      const productName = e.parameter.productName || '';
      const price = e.parameter.price || '';
      const size = e.parameter.size || ''; // New parameter for size
      const color = e.parameter.color || ''; // New parameter for color
      const comment = e.parameter.comment || '';
      const photo = e.parameter.photo || '';
  
      // Append the data to the sheet
      sheet.appendRow([
        // new Date(),  // Uncomment if you want to log the timestamp
        productId,
        productName,
        price,
        size, // Include size in the row
        color, // Include color in the row
        comment,
        photo
      ]);
  
      return ContentService.createTextOutput(JSON.stringify({ status: 'success', message: 'Data added successfully' }))
                           .setMimeType(ContentService.MimeType.JSON);
      
    } catch (error) {
      Logger.log(error);
      return ContentService.createTextOutput(JSON.stringify({ status: 'error', message: error.message }))
                           .setMimeType(ContentService.MimeType.JSON);
    }
  }
  