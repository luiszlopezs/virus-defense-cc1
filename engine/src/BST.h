#ifndef BST_H
#define BST_H

// BSTNode represents a node in the Binary Search Tree.
// Since multiple cells can have the same degree, we use the tuple (degree, node_id) as the unique key.
// node_id is computed as row * 12 + col (range 0 to 143).
struct BSTNode {
    int degree;
    int node_id;
    BSTNode* left;
    BSTNode* right;
};

// BST manages the binary search tree of nodes, allowing us to find the node with maximum connectivity.
class BST {
private:
    BSTNode* root;

    BSTNode* insertHelper(BSTNode* node, int node_id, int degree);
    BSTNode* removeHelper(BSTNode* node, int node_id, int degree);
    BSTNode* findMin(BSTNode* node) const;
    void destroyTree(BSTNode* node);

public:
    BST();
    ~BST();

    void insert(int node_id, int degree);
    void remove(int node_id, int degree);
    int findMax() const;
    void update(int node_id, int old_deg, int new_deg);
};

#endif // BST_H
