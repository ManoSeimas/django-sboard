function(doc) {
    if (doc.tags) {
        for (var i=0; i<doc.tags.length; i++) {
            emit(doc.tags[i], null);
        }
    }
}
