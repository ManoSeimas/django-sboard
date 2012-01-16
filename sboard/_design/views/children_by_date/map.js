function(doc) {
    if(doc.parents) {
        var parent = doc.parents[doc.parents.length-1];
        emit( [parent, doc.created], null );
    }
}
