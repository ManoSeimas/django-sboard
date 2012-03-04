function(doc) {
    if (doc.parents) {
        for (var i=0; i<doc.parents.length; i++) {
            emit(doc._id, {_id: doc.parents[i]});
        }
    }
}
