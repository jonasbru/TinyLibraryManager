function searchBookG(field) {
//    alert(field)
//    alert($("#" + field).val())

    $.getJSON('https://www.googleapis.com/books/v1/volumes?q=' + encodeURIComponent($("#" + field).val()) + '&key=AIzaSyAli6dG_tPsW012MSzbsVxJBoQljpJogIc', function (data) {
        var items = [];
        $.each(data.items, function (key, val) {
                var line = '<tr>';
                line += '<td>' + val.volumeInfo.title + '</td>';
                line += '<td>' + val.volumeInfo.authors + '</td>';
                line += '<td>' + val.volumeInfo.publisher + '</td>';
                if (val.volumeInfo.imageLinks) {
                    line += '<td><img src=' + val.volumeInfo.imageLinks.smallThumbnail + ' alt="img"/></td>';
                }

                line += '<td><form action="/add" method="post">';
                line += '<input type="hidden" name="title" value="' + val.volumeInfo.title + '" >';
                if (val.volumeInfo.description) {
                    line += '<input type="hidden" name="description" value="' + val.volumeInfo.description.replace(/\\/g, "\\\\") + '" >';
                }
                if (val.volumeInfo.authors) {
                    line += '<input type="hidden" name="authors" value="' + val.volumeInfo.authors + '" >';
                }
                if (val.volumeInfo.publisher) {
                    line += '<input type="hidden" name="publisher" value="' + val.volumeInfo.publisher + '" >';
                }
                if (val.volumeInfo.publisherDate) {
                    line += '<input type="hidden" name="publisherDate" value="' + val.volumeInfo.publisherDate + '" >';
                }
                if (val.volumeInfo.industryIdentifiers) {
                    line += '<input type="hidden" name="ISBN" value="' + val.volumeInfo.industryIdentifiers.ISBN_13 + '" >';
                }
                if (val.volumeInfo.imageLinks) {
                    line += '<input type="hidden" name="thumbnail" value="' + val.volumeInfo.imageLinks.thumbnail + '" >';
                }
                if (val.volumeInfo.accessInfo) {
                    line += '<input type="hidden" name="webReaderLink" value="' + val.accessInfo.webReaderLink + '" >';
                }
                line += '<input type="submit" value="Add" class="btn btn-primary">';
                line += '</form></td>';

                items.push(line);
            }
        )
        ;
        $('#tabResults').html(items.join(''));
        console.log(data)
    });
}
