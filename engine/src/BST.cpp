#include "BST.h"

// Constructor: Initializes the root of the tree to nullptr.
BST::BST() : root(nullptr) {}

// Destructor: Cleans up all nodes recursively via destroyTree.
BST::~BST() {
    destroyTree(root);
    root = nullptr;
}

// destroyTree: Traverses the tree in post-order and deletes each node.
void BST::destroyTree(BSTNode* node) {
    if (node != nullptr) {
        destroyTree(node->left);
        destroyTree(node->right);
        delete node;
    }
}

// insert: Adds a new (node_id, degree) pair into the BST.
void BST::insert(int node_id, int degree) {
    root = insertHelper(root, node_id, degree);
}

// insertHelper: Recursively inserts a node. We order nodes by degree first.
// If degrees are equal, we order by node_id to guarantee unique positions in the tree.
BSTNode* BST::insertHelper(BSTNode* node, int node_id, int degree) {
    if (node == nullptr) {
        BSTNode* newNode = new BSTNode();
        newNode->degree = degree;
        newNode->node_id = node_id;
        newNode->left = nullptr;
        newNode->right = nullptr;
        return newNode;
    }

    if (degree < node->degree || (degree == node->degree && node_id < node->node_id)) {
        node->left = insertHelper(node->left, node_id, degree);
    } else {
        node->right = insertHelper(node->right, node_id, degree);
    }
    return node;
}

// remove: Removes a specific (node_id, degree) pair from the BST.
void BST::remove(int node_id, int degree) {
    root = removeHelper(root, node_id, degree);
}

// removeHelper: Recursively finds and deletes the node.
BSTNode* BST::removeHelper(BSTNode* node, int node_id, int degree) {
    if (node == nullptr) return nullptr;

    if (degree < node->degree || (degree == node->degree && node_id < node->node_id)) {
        node->left = removeHelper(node->left, node_id, degree);
    } else if (degree > node->degree || (degree == node->degree && node_id > node->node_id)) {
        node->right = removeHelper(node->right, node_id, degree);
    } else {
        // Node found! Handle the three standard BST deletion cases:
        if (node->left == nullptr) {
            BSTNode* temp = node->right;
            delete node;
            return temp;
        } else if (node->right == nullptr) {
            BSTNode* temp = node->left;
            delete node;
            return temp;
        }

        // Case with two children: Get the inorder successor (smallest in the right subtree)
        BSTNode* temp = findMin(node->right);
        node->degree = temp->degree;
        node->node_id = temp->node_id;
        node->right = removeHelper(node->right, temp->node_id, temp->degree);
    }
    return node;
}

// findMin: Helper that returns the node with the minimum key in the subtree (leftmost node).
BSTNode* BST::findMin(BSTNode* node) const {
    BSTNode* current = node;
    while (current && current->left != nullptr) {
        current = current->left;
    }
    return current;
}

// findMax: Traverses to the rightmost node in the BST to find the maximum key.
// Returns the node_id of this node, or -1 if the tree is empty.
// In our composite key, the rightmost node represents the node with the highest degree.
int BST::findMax() const {
    if (root == nullptr) return -1;
    BSTNode* current = root;
    while (current->right != nullptr) {
        current = current->right;
    }
    return current->node_id;
}

// update: Updates a node's key when its connectivity degree changes.
// Since changing a key requires restructuring the BST, we remove the old entry and insert the new one.
// This is an O(log N) operation on average.
void BST::update(int node_id, int old_deg, int new_deg) {
    remove(node_id, old_deg);
    insert(node_id, new_deg);
}

// Note on BST Balancing:
// Since the maximum number of grid elements is 144 (for a 12x12 grid) and the primary search key (degree)
// is restricted to the range [1, 4] (no diagonal connections), the tree depth is naturally bounded.
// The key space is extremely small, meaning the tree cannot degrade into a long linear chain of depth 144.
// Therefore, complex self-balancing algorithms like AVL or Red-Black trees are not required here.
