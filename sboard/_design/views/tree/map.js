function(doc) {
    if (doc.parents) {
        for (var i=0; i<doc.parents.length; i++) {
            emit([doc.parents[i], i], null);
        }
    }
}
